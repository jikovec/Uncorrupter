from io import BytesIO

from PIL import Image

from file_uncorrupter.classification import classify_record
from file_uncorrupter.engines.media_v2 import BaselineRecoveryEngineV2
from file_uncorrupter.intake import build_file_record


def make_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), (123, 100, 80))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def test_classifies_missing_eoi_as_jpeg_missing_eoi(tmp_path):
    data = make_jpeg_bytes()[:-2]
    path = tmp_path / "missing_eoi.jpg"
    path.write_bytes(data)
    record = build_file_record(tmp_path, path, data)
    classification = classify_record(record, data)
    assert classification.family == "jpeg"
    assert classification.label == "jpeg_missing_eoi"


def test_classifies_missing_soi_internal_structure(tmp_path):
    original = make_jpeg_bytes()
    data = original[2:]
    path = tmp_path / "missing_soi.jpg"
    path.write_bytes(data)
    record = build_file_record(tmp_path, path, data)
    classification = classify_record(record, data)
    assert classification.family == "jpeg"
    assert classification.label == "jpeg_missing_soi_internal_structure"


def test_declared_video_does_not_route_embedded_jpeg_to_jpeg_engine(tmp_path):
    data = b"BROKEN_MP4_HEADER" + make_jpeg_bytes()
    path = tmp_path / "damaged.mp4"
    path.write_bytes(data)
    record = build_file_record(tmp_path, path, data)

    assert record.byte0_kind == "unknown"
    assert record.anywhere_kind == "jpeg"

    classification = classify_record(record, data)
    candidates = BaselineRecoveryEngineV2().generate_candidates(record, data, classification)

    assert classification.family == "mp4"
    assert classification.label == "mp4_declared_only"
    assert {candidate.family for candidate in candidates} == {"mp4"}
    assert {candidate.strategy_id for candidate in candidates} == {"full_file"}
