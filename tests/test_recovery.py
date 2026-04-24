import io
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from file_uncorrupter.classification import classify_record
from file_uncorrupter.constants import DHT, SOS
from file_uncorrupter.decoders import ffmpeg_available
from file_uncorrupter.engines.jpeg_v1 import standard_dht_segments, standard_dqt_segments
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


def strip_sos_segment(data: bytes) -> bytes:
    sos = data.index(SOS)
    length = int.from_bytes(data[sos + 2:sos + 4], "big")
    return data[:sos] + data[sos + 2 + length:]


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


def test_pipeline_rebuilds_header_from_scattered_segments(tmp_path):
    original = make_jpeg_bytes()
    sos = original.index(b"\xff\xda")

    moved_tail = bytearray()
    for marker in (b"\xff\xe0", b"\xff\xdb", b"\xff\xc0", b"\xff\xc4"):
        start = original.find(marker)
        if start != -1:
            length = int.from_bytes(original[start + 2:start + 4], "big")
            moved_tail.extend(original[start:start + 2 + length])
    damaged = original[sos:] + b"JUNK" + bytes(moved_tail)

    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    outcome, _ = pipeline.recover_one(record, damaged, classification, output_root, save_raw_candidates=False)

    assert classification.label == "jpeg_missing_soi_internal_structure"
    assert outcome.decode.ok is True
    assert outcome.candidate is not None
    assert "rebuild_header" in outcome.candidate.strategy_id


def test_pipeline_recovers_missing_soi_and_missing_sos(tmp_path):
    original = make_jpeg_bytes()
    damaged = strip_sos_segment(original)[2:]

    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    outcome, _ = pipeline.recover_one(record, damaged, classification, output_root, save_raw_candidates=False)

    assert classification.label == "jpeg_missing_soi_internal_structure"
    assert outcome.decode.ok is True
    assert outcome.candidate is not None
    assert "synthetic_sos" in outcome.candidate.strategy_id


@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg is required for video recovery tests")
def test_pipeline_recovers_prefixed_mp4_via_signature_offset(tmp_path):
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()

    good_mp4 = tmp_path / "good.mp4"
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=red:s=64x64:d=1",
        "-pix_fmt", "yuv420p",
        str(good_mp4),
    ]
    subprocess.run(cmd, check=True)
    damaged = b"PREFIX_GARBAGE" + good_mp4.read_bytes()

    file_path = input_root / "broken.bin"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="baseline-v2")
    outcome, _ = pipeline.recover_one(record, damaged, classification, output_root, save_raw_candidates=False)

    assert classification.family == "mp4"
    assert classification.label == "isobmff_signature_away_from_byte0"
    assert outcome.decode.ok is True
    assert outcome.artifacts
    assert any(artifact.artifact_type in {"video", "preview_frame", "frame_set"} for artifact in outcome.artifacts)


def test_missing_soi_candidates_include_windowed_rebuilds(tmp_path):
    original = make_jpeg_bytes()
    damaged = original[2:] + b"GARBAGE_TRAILER" * 4
    input_root = tmp_path / "input"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    candidates = pipeline.engine.generate_candidates(record, damaged, classification)

    strategy_ids = {candidate.strategy_id for candidate in candidates}
    assert classification.label == "jpeg_missing_soi_internal_structure"
    assert any(strategy_id.startswith("rebuild_header_from_segments_") for strategy_id in strategy_ids)
    assert any(strategy_id.startswith("sos_window_rebuild_header_back_") for strategy_id in strategy_ids)
    assert any(strategy_id.startswith("classification_hint_synthetic_soi_back_") for strategy_id in strategy_ids)


def test_missing_soi_without_sos_candidates_include_synthetic_sos_rebuilds(tmp_path):
    original = make_jpeg_bytes()
    damaged = strip_sos_segment(original)[2:] + b"TAIL_NOISE" * 3
    input_root = tmp_path / "input"
    input_root.mkdir()
    file_path = input_root / "sample.jpg"
    file_path.write_bytes(damaged)

    record = build_file_record(input_root, file_path, damaged)
    classification = classify_record(record, damaged)
    pipeline = RecoveryPipeline(engine_name="jpeg-v1")
    candidates = pipeline.engine.generate_candidates(record, damaged, classification)

    strategy_ids = {candidate.strategy_id for candidate in candidates}
    assert classification.label == "jpeg_missing_soi_internal_structure"
    assert any(strategy_id.startswith("rebuild_header_with_synthetic_sos_") for strategy_id in strategy_ids)
    assert any(strategy_id.startswith("rebuild_header_with_synthetic_sos_minimal_") for strategy_id in strategy_ids)


def test_standard_color_tables_include_multicomponent_segments():
    dht = standard_dht_segments()
    dqt = standard_dqt_segments()
    assert dht.count(b"\xff\xc4") >= 4
    assert dqt.count(b"\xff\xdb") >= 2
