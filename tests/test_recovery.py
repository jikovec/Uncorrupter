import io
from pathlib import Path

from PIL import Image

from file_uncorrupter.classification import classify_record
from file_uncorrupter.constants import DHT, SOI, SOS
from file_uncorrupter.engines.jpeg_v1 import standard_dht_segments
from file_uncorrupter.intake import build_file_record
from file_uncorrupter.pipeline import RecoveryPipeline


def make_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (48, 48), (120, 90, 60))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def strip_dht_segments(data: bytes) -> bytes:
    result = bytearray()
    i = 0
    while i < len(data):
        if i + 1 < len(data) and data[i] == 0xFF and data[i + 1] == 0xC4:
            if i + 4 > len(data):
                break
            length = int.from_bytes(data[i + 2:i + 4], "big")
            i += 2 + length
            continue
        result.append(data[i])
        i += 1
    return bytes(result)


def test_pipeline_recovers_missing_eoi(tmp_path):
    original = make_jpeg_bytes()
    damaged = original[:-2]
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    outcome, _ = pipeline.recover_one(record, damaged, classification, output_root, save_raw_candidates=True)

    assert outcome.decode.ok is True
    assert outcome.decode.output_path is not None
    assert outcome.decode.output_path.exists()


def test_pipeline_recovers_missing_soi(tmp_path):
    original = make_jpeg_bytes()
    damaged = original[2:]
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    outcome, _ = pipeline.recover_one(record, damaged, classification, output_root, save_raw_candidates=False)

    assert outcome.decode.ok is True


def test_pipeline_recovers_missing_dht(tmp_path):
    original = make_jpeg_bytes()
    assert standard_dht_segments() != b""
    damaged = strip_dht_segments(original)
    assert DHT not in damaged
    assert SOS in damaged

    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    outcome, _ = pipeline.recover_one(record, damaged, classification, output_root, save_raw_candidates=False)

    assert classification.label == "jpeg_missing_dht"
    assert outcome.decode.ok is True
