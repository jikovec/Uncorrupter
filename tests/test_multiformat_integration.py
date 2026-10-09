from __future__ import annotations

import io
import zipfile

from PIL import Image

from file_uncorrupter.budgets import ResourceLimits
from file_uncorrupter.db import connect, fetch_summary, start_run, transition_run
from file_uncorrupter.handlers.base import RecoveryGoal
from file_uncorrupter.pipeline import RecoveryPipeline
from file_uncorrupter.reporting import build_final_manifest


def _image(fmt: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 6), (20, 40, 60)).save(buffer, format=fmt)
    return buffer.getvalue()


def _docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><document><body><p><t>Recovered package text</t></p></body></document>',
        )
    return buffer.getvalue()


def _zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("safe/member.txt", "archive payload")
    return buffer.getvalue()


def _pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 37 >>\nstream\nBT (Recovered PDF text) Tj ET\nendstream\nendobj\n"
        b"trailer\n<< /Root 1 0 R /Size 5 >>\nstartxref\n0\n%%EOF\n"
    )


def _wav() -> bytes:
    return b"RIFF" + (8).to_bytes(4, "little") + b"WAVE" + b"fmt " + (0).to_bytes(4, "little")


def test_registered_text_archive_document_pdf_image_video_audio_and_jpeg_routes_persist(tmp_path):
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    sources = {
        "note.md": b"# Recovered heading\n",
        "bundle.zip": _zip(),
        "document.docx": _docx(),
        "document.pdf": _pdf(),
        "picture.png": _image("PNG"),
        "photo.jpg": _image("JPEG"),
        "sound.wav": _wav(),
        "clip.mp4": b"junk" + (20).to_bytes(4, "big") + b"ftyp" + b"isom\x00\x00\x00\x00isom",
    }
    for name, payload in sources.items():
        (input_root / name).write_bytes(payload)

    goals = {
        "note.md": RecoveryGoal.EXTRACT,
        "bundle.zip": RecoveryGoal.EXTRACT,
        "document.docx": RecoveryGoal.EXTRACT,
        "document.pdf": RecoveryGoal.EXTRACT,
        "picture.png": RecoveryGoal.NORMALIZE,
        "photo.jpg": RecoveryGoal.REPAIR,
        "sound.wav": RecoveryGoal.REPAIR,
        "clip.mp4": RecoveryGoal.REPAIR,
    }
    pipeline = RecoveryPipeline(limits=ResourceLimits(max_workers=1))
    executions = [
        pipeline.process_path(input_root, input_root / name, output_root=output_root, goals=(goal,))
        for name, goal in goals.items()
    ]

    assert {execution.classification.family for execution in executions} == {
        "markdown", "zip", "docx", "pdf", "png", "jpeg", "wav", "mp4"
    }
    assert all(execution.status in {"recovered", "partial"} for execution in executions), [
        (
            execution.record.relative_path.name if execution.record else str(execution.analysis.path),
            execution.status,
            execution.error_code,
            [item.outcome.decode.error for item in execution.goals],
        )
        for execution in executions
    ]
    assert any(execution.artifacts for execution in executions if execution.record.relative_path.name not in {"sound.wav"})

    with connect(tmp_path / "run.sqlite3") as conn:
        run_id = start_run(conn, "recover", input_root, output_root, "baseline-v2")
        transition_run(conn, run_id, "running")
        for execution in executions:
            pipeline.persist_execution(conn, run_id, execution)
        transition_run(conn, run_id, "partial" if any(item.status == "partial" for item in executions) else "completed")
        summary = fetch_summary(conn, run_id)
        manifest = build_final_manifest(conn, run_id)
        typed_counts = {
            "text_spans": conn.execute("SELECT COUNT(*) FROM text_spans").fetchone()[0],
            "archive_members": conn.execute("SELECT COUNT(*) FROM archive_members").fetchone()[0],
            "document_parts": conn.execute("SELECT COUNT(*) FROM document_parts").fetchone()[0],
            "media_streams": conn.execute("SELECT COUNT(*) FROM media_streams").fetchone()[0],
        }

    assert summary["total_files"] == len(sources)
    assert len(manifest["files"]) == len(sources)
    assert typed_counts["text_spans"] > 0
    assert typed_counts["archive_members"] > 0
    assert typed_counts["document_parts"] > 0
    assert "fidelity" in manifest["benchmark"]
