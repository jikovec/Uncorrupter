from __future__ import annotations

import hashlib
import io

import pytest
from PIL import Image

from file_uncorrupter.budgets import ResourceLimits
from file_uncorrupter.byte_source import FileByteSource
from file_uncorrupter.classification import classify_record
from file_uncorrupter.intake import build_file_record, build_file_record_from_source, iter_input_files
from file_uncorrupter.pipeline import RecoveryPipeline
from file_uncorrupter.workspace import build_workspace_layout


def jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (12, 8), (20, 30, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_streaming_record_matches_eager_identity_and_discovery_is_deterministic(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "z.jpg").write_bytes(jpeg_bytes())
    (root / "a.jpg").write_bytes(jpeg_bytes())

    assert [path.name for path in iter_input_files(root, recursive=False, all_files=True)] == ["a.jpg", "z.jpg"]
    path = root / "a.jpg"
    eager = build_file_record(root, path, path.read_bytes())
    source = FileByteSource(path, limits=ResourceLimits(max_scanned_bytes=1 << 20))
    streamed = build_file_record_from_source(root, source, chunk_size=31)

    assert streamed.sha256 == eager.sha256
    assert streamed.size == eager.size
    assert streamed.byte0_kind == "jpeg"
    assert streamed.relative_path == eager.relative_path


def test_recovery_does_not_mutate_source_or_preexisting_output(tmp_path):
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    output_root.mkdir()
    source = input_root / "sample.jpg"
    source.write_bytes(jpeg_bytes())
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = output_root / "sample.jpg"
    destination.write_bytes(b"pre-existing")
    destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    data = source.read_bytes()
    record = build_file_record(input_root, source, data)
    classification = classify_record(record, data)

    outcome, raw_path = RecoveryPipeline("jpeg-v1").recover_one(
        record, data, classification, output_root, save_raw_candidates=True
    )

    assert outcome.decode.ok is False
    assert "destination already exists" in outcome.decode.error
    assert raw_path is None
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == destination_hash


def test_changed_source_is_rejected_before_artifact_publication(tmp_path):
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    source = input_root / "sample.jpg"
    original = jpeg_bytes()
    source.write_bytes(original)
    record = build_file_record(input_root, source, original)
    classification = classify_record(record, original)
    source.write_bytes(original + b"changed")

    outcome, _ = RecoveryPipeline("jpeg-v1").recover_one(
        record, original, classification, output_root, save_raw_candidates=False
    )

    assert outcome.decode.error == "source_changed_before_recovery"
    assert not output_root.exists()


def test_workspace_snapshots_are_atomic_and_no_clobber(tmp_path):
    layout = build_workspace_layout(
        input_root=tmp_path / "input",
        db_path=tmp_path / "runs.sqlite3",
        workspace_root=tmp_path / "workspace",
    )
    layout.ensure()
    first = layout.write_config_snapshot(1, {"workers": 1})

    with pytest.raises(FileExistsError):
        layout.write_config_snapshot(1, {"workers": 2})

    assert '"workers": 1' in first.read_text(encoding="utf-8")
