from __future__ import annotations

import hashlib
import tracemalloc
import zipfile
from pathlib import Path

import pytest

from file_uncorrupter.budgets import BudgetTracker, ResourceLimits
from file_uncorrupter.byte_source import FileByteSource
from file_uncorrupter.cancellation import CancellationToken
from file_uncorrupter.handlers.archive import ArchiveHandler
from file_uncorrupter.handlers.base import HandlerContext, RecoveryGoal
from file_uncorrupter.handlers.image import ImageHandler
from file_uncorrupter.handlers.media import MediaHandler
from file_uncorrupter.handlers.package_document import PackageDocumentHandler
from file_uncorrupter.handlers.pdf import PDFHandler
from file_uncorrupter.types import Classification, FileRecord

from tests.fixtures import openxml_bytes, simple_pdf_bytes, tiff_bytes, zip_bytes


def _context(tmp_path: Path, name: str, payload: bytes, family: str) -> HandlerContext:
    source_path = tmp_path / "input" / name
    source_path.parent.mkdir(exist_ok=True)
    source_path.write_bytes(payload)
    limits = ResourceLimits(
        max_source_bytes=len(payload) + 1,
        max_scanned_bytes=max(1 << 20, len(payload) * 24),
        max_candidate_bytes=32,
        max_materialized_bytes=32,
        max_archive_member_bytes=max(1 << 20, len(payload) * 2),
        max_decompressed_bytes=max(2 << 20, len(payload) * 4),
        max_output_bytes=max(2 << 20, len(payload) * 4),
        max_workers=1,
    )
    budget = BudgetTracker(limits.budget_limits(), scope=f"test:{name}")
    source = FileByteSource(source_path, limits=limits, budget=budget)
    record = FileRecord(
        path=source_path,
        relative_path=Path(name),
        size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        declared_kind=source_path.suffix.removeprefix("."),
        byte0_kind=family,
        anywhere_kind=family,
    )
    return HandlerContext(
        source=source,
        record=record,
        classification=Classification(family, family, 1.0),
        limits=limits,
        budget=budget,
        cancellation=CancellationToken(),
        output_root=tmp_path / "output" / name,
    )


@pytest.mark.parametrize(
    ("name", "family", "handler", "goal", "payload"),
    [
        (
            "large.zip",
            "archive",
            ArchiveHandler(),
            RecoveryGoal.EXTRACT,
            zip_bytes({"payload.bin": bytes(range(256)) * 32}, compression=zipfile.ZIP_STORED),
        ),
        ("large.docx", "package_document", PackageDocumentHandler(), RecoveryGoal.EXTRACT, openxml_bytes("docx")),
        ("large.pdf", "pdf", PDFHandler(), RecoveryGoal.EXTRACT, simple_pdf_bytes() + (b" \n" * 256)),
        ("large.tiff", "image", ImageHandler(), RecoveryGoal.PREVIEW, tiff_bytes(frames=3)),
        (
            "large.avi",
            "media",
            MediaHandler(),
            RecoveryGoal.REPAIR,
            b"RIFF" + (1).to_bytes(4, "little") + b"AVI " + (b"\0" * 4096),
        ),
    ],
)
def test_public_handler_paths_work_below_source_materialization_size(
    tmp_path: Path,
    name: str,
    family: str,
    handler,
    goal: RecoveryGoal,
    payload: bytes,
) -> None:
    context = _context(tmp_path, name, payload, family)
    assert context.source.size > context.limits.max_materialized_bytes

    inspection = handler.inspect(context)
    plans = handler.plan(context, goal)
    assert inspection.family == family
    assert plans and plans[0].estimated_materialized_bytes == 0

    outcome = handler.execute(context, plans[0])

    assert outcome.decode.ok, outcome.decode.error
    assert context.budget.consumed("materialized_bytes") == 0
    assert any(path.is_file() for path in context.output_root.rglob("*"))


def test_large_stored_zip_validation_has_bounded_python_memory(tmp_path: Path) -> None:
    member_path = tmp_path / "member.bin"
    member_bytes = 16 * (1 << 20)
    with member_path.open("wb") as handle:
        handle.truncate(member_bytes)
    archive_path = tmp_path / "large.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.write(member_path, "member.bin")

    archive_bytes = archive_path.stat().st_size
    limits = ResourceLimits(
        max_source_bytes=archive_bytes + 1,
        max_scanned_bytes=archive_bytes * 3,
        max_materialized_bytes=1 << 20,
        max_archive_member_bytes=member_bytes + 1,
        max_decompressed_bytes=member_bytes + 1,
        max_workers=1,
    )
    budget = BudgetTracker(limits.budget_limits(), scope="large-zip")
    source = FileByteSource(archive_path, limits=limits, budget=budget)

    tracemalloc.start()
    result = ArchiveHandler().recover_source(source, suffix=".zip", limits=limits, goal=RecoveryGoal.REPAIR.value)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result.outcome == "validated_original"
    assert budget.consumed("materialized_bytes") == 0
    assert peak < 12 * (1 << 20)
