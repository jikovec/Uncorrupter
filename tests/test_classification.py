from pathlib import Path

from PIL import Image

from file_uncorrupter.classification import classify_record
from file_uncorrupter.intake import build_file_record


def make_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), (123, 100, 80))
    path = Path("/tmp/sample.jpg")
    image.save(path, format="JPEG", quality=85)
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data


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
