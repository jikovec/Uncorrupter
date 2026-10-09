from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from file_uncorrupter.budgets import ResourceLimits
from file_uncorrupter.cancellation import CancellationToken, CancelledError
from file_uncorrupter.db import connect, start_run, transition_run
from file_uncorrupter.decoders import recover_media_goal_with_ffmpeg
from file_uncorrupter.handlers.base import RecoveryGoal
from file_uncorrupter.handlers.media import MediaHandler
from file_uncorrupter.pipeline import RecoveryPipeline


def mp4_box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + kind + payload


def test_mp4_prefix_is_removed_and_box_structure_is_recorded():
    mp4 = mp4_box(b"ftyp", b"isom\x00\x00\x00\x00isom") + mp4_box(b"moov", b"") + mp4_box(b"mdat", b"data")
    result = MediaHandler().recover_bytes(b"prefix" + mp4, suffix=".mp4")

    assert result.family == "mp4"
    assert result.outcome == "repaired"
    assert result.prefix_bytes == 6
    assert result.rebuilt_bytes == mp4
    assert [item["type"] for item in result.structures["boxes"]] == ["ftyp", "moov", "mdat"]


def test_truncated_mp4_and_ebml_are_partial_not_full():
    truncated = mp4_box(b"ftyp", b"isom\x00\x00\x00\x00") + (100).to_bytes(4, "big") + b"mdat" + b"short"
    mp4_result = MediaHandler().recover_bytes(truncated, suffix=".mp4")
    assert mp4_result.outcome == "partial_content"
    assert mp4_result.structures["truncated_box"] is True

    ebml = b"junk" + b"\x1a\x45\xdf\xa3" + b"\x81\x00" + b"webm"
    ebml_result = MediaHandler().recover_bytes(ebml, suffix=".webm")
    assert ebml_result.family == "webm"
    assert ebml_result.prefix_bytes == 4
    assert ebml_result.outcome == "repaired"


def test_riff_avi_and_wav_sizes_are_repaired():
    avi = b"RIFF" + (1).to_bytes(4, "little") + b"AVI " + b"LIST" + (0).to_bytes(4, "little")
    avi_result = MediaHandler().recover_bytes(avi, suffix=".avi")
    assert avi_result.family == "avi"
    assert avi_result.outcome == "repaired"
    assert int.from_bytes(avi_result.rebuilt_bytes[4:8], "little") == len(avi) - 8

    wav = b"RIFF" + (4).to_bytes(4, "little") + b"WAVE" + b"fmt " + (0).to_bytes(4, "little")
    wav_result = MediaHandler().recover_bytes(wav, suffix=".wav")
    assert wav_result.family == "wav"


def ts_packet(pid: int, continuity: int) -> bytes:
    return bytes([0x47, (pid >> 8) & 0x1F, pid & 0xFF, 0x10 | continuity]) + b"\xff" * 184


def test_mpeg_ts_desync_and_continuity_are_reported():
    data = b"noise" + b"".join(ts_packet(256, value) for value in [0, 1, 3, 4, 5])
    result = MediaHandler().recover_bytes(data, suffix=".ts")

    assert result.family == "mpegts"
    assert result.outcome == "repaired"
    assert result.prefix_bytes == 5
    assert result.structures["packets"] == 5
    assert result.structures["continuity_discontinuities"] == 1


def test_flv_asf_and_audio_headers_are_detected_honestly():
    samples = [
        (".flv", b"FLV\x01\x05\x00\x00\x00\x09", "flv"),
        (".asf", bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c") + b"x" * 32, "asf"),
        (".mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x64", "mp3"),
        (".flac", b"fLaC" + b"\x00" * 32, "flac"),
        (".aac", b"\xff\xf1\x50\x80\x00\x1f\xfc", "aac"),
        (".ogg", b"OggS\x00" + b"\x00" * 32, "ogg"),
    ]
    for suffix, payload, family in samples:
        result = MediaHandler().recover_bytes(payload, suffix=suffix)
        assert result.family == family
        assert result.outcome in {"validated_original", "partial_content"}


def test_optional_media_tool_absence_is_explicit(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    mp4 = mp4_box(b"ftyp", b"isom\x00\x00\x00\x00") + mp4_box(b"mdat", b"data")
    result = MediaHandler().recover_bytes(mp4, suffix=".mp4", request_tool_validation=True)

    assert result.tool_evidence["available"] is False
    assert "not_found" in result.tool_evidence["error"] or "disabled" in result.tool_evidence["error"]


def _install_fake_media_tools(monkeypatch):
    monkeypatch.delenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", raising=False)
    monkeypatch.setattr("file_uncorrupter.decoders.FFMPEG_PATH", "fake-ffmpeg")
    monkeypatch.setattr("file_uncorrupter.decoders.FFPROBE_PATH", "fake-ffprobe")

    def fake_probe(executable, **_kwargs):
        return SimpleNamespace(
            available=True,
            resolved_path=str(executable),
            version=f"{Path(str(executable)).name} fake 1.0",
            error=None,
        )

    preview = io.BytesIO()
    Image.new("RGB", (4, 3), (20, 40, 60)).save(preview, format="PNG")
    preview_bytes = preview.getvalue()

    def process_result(*, stdout=b"", stderr=b"", returncode=0, cancelled=False):
        return SimpleNamespace(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_sha256=hashlib.sha256(stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr).hexdigest(),
            timed_out=False,
            cancelled=cancelled,
            output_truncated=False,
            duration_seconds=0.01,
            cleanup_ok=True,
        )

    def fake_run(command, _policy, *, cancellation=None):
        executable = Path(command[0]).name
        target = Path(command[-1])
        if executable == "fake-ffprobe":
            if "stream-000-video" in target.name:
                streams = [{"index": 0, "codec_type": "video", "codec_name": "h264", "width": 4, "height": 3, "nb_frames": "12", "duration": "2.0"}]
            elif "stream-001-audio" in target.name:
                streams = [{"index": 0, "codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000", "duration": "2.0"}]
            else:
                streams = [
                    {"index": 0, "codec_type": "video", "codec_name": "h264", "width": 4, "height": 3, "nb_frames": "12", "duration": "2.0"},
                    {"index": 1, "codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000", "duration": "2.0"},
                ]
            payload = json.dumps({"streams": streams, "format": {"format_name": "matroska", "duration": "2.0", "size": "64"}}).encode()
            return process_result(stdout=payload)
        if target.suffix == ".png":
            target.write_bytes(preview_bytes)
        else:
            target.write_bytes(b"validated-matroska:" + target.name.encode("ascii"))
        return process_result()

    monkeypatch.setattr("file_uncorrupter.decoders.probe_tool", fake_probe)
    monkeypatch.setattr("file_uncorrupter.decoders.run_process", fake_run)


@pytest.mark.parametrize(
    ("goal", "artifact_types", "grade"),
    [
        ("normalize", ["normalized"], "validated_normalized"),
        ("extract", ["extracted", "extracted"], "partial_content"),
        ("preview", ["preview"], "preview_only"),
    ],
)
def test_ffmpeg_goals_validate_exact_outputs_and_return_typed_evidence(tmp_path, monkeypatch, goal, artifact_types, grade):
    _install_fake_media_tools(monkeypatch)
    output_root = tmp_path / goal

    decoded, artifacts = recover_media_goal_with_ffmpeg(
        mp4_box(b"ftyp", b"isom\x00\x00\x00\x00") + mp4_box(b"mdat", b"data"),
        "mp4",
        output_root,
        goal,
    )

    assert decoded.ok is True
    assert [artifact.artifact_type for artifact in artifacts] == artifact_types
    assert decoded.telemetry["fidelity_grade"] == grade
    assert decoded.telemetry["streams"][0]["codec"] == "h264"
    assert decoded.telemetry["format"]["duration_ms"] == 2000
    assert decoded.telemetry["tool"]["available"] is True
    assert decoded.telemetry["tool"]["runs"]
    for artifact in artifacts:
        assert artifact.path.is_file()
        assert artifact.sha256 == hashlib.sha256(artifact.path.read_bytes()).hexdigest()
        assert artifact.validators[0]["validated_sha256"] == artifact.sha256
        assert artifact.validation_state.endswith("validated")


def test_ffmpeg_goal_propagates_cancellation_before_publication(tmp_path, monkeypatch):
    _install_fake_media_tools(monkeypatch)
    token = CancellationToken()

    def cancelled_run(command, _policy, *, cancellation=None):
        if Path(command[0]).name == "fake-ffprobe":
            payload = json.dumps({"streams": [{"index": 0, "codec_type": "video", "codec_name": "h264"}], "format": {}}).encode()
            empty = hashlib.sha256(b"").hexdigest()
            return SimpleNamespace(returncode=0, stdout=payload, stderr=b"", stdout_sha256=hashlib.sha256(payload).hexdigest(), stderr_sha256=empty, timed_out=False, cancelled=False, output_truncated=False, duration_seconds=0.01, cleanup_ok=True)
        token.cancel("unit-test")
        empty = hashlib.sha256(b"").hexdigest()
        return SimpleNamespace(returncode=None, stdout=b"", stderr=b"", stdout_sha256=empty, stderr_sha256=empty, timed_out=False, cancelled=True, output_truncated=False, duration_seconds=0.01, cleanup_ok=True)

    monkeypatch.setattr("file_uncorrupter.decoders.run_process", cancelled_run)
    with pytest.raises(CancelledError, match="unit-test"):
        recover_media_goal_with_ffmpeg(b"media", "mp4", tmp_path / "output", "normalize", cancellation=token)
    assert not list((tmp_path / "output").glob("*"))


def test_ffmpeg_stream_timing_coverage_tool_and_fidelity_evidence_persist(tmp_path, monkeypatch):
    _install_fake_media_tools(monkeypatch)
    source_root = tmp_path / "input"
    source_root.mkdir()
    source = source_root / "clip.mp4"
    source.write_bytes(mp4_box(b"ftyp", b"isom\x00\x00\x00\x00") + mp4_box(b"mdat", b"data"))
    output_root = tmp_path / "output"
    pipeline = RecoveryPipeline(limits=ResourceLimits(max_workers=1))

    execution = pipeline.process_path(
        source_root,
        source,
        output_root=output_root,
        goals=(RecoveryGoal.NORMALIZE,),
    )

    assert execution.status == "recovered"
    assert execution.goals[0].outcome.grade == "validated_normalized"
    assert execution.goals[0].outcome.decode.telemetry["decoded_coverage"]["fraction"] == 1.0
    assert execution.goals[0].outcome.decode.telemetry["tool"]["duration_seconds"] > 0

    with connect(tmp_path / "run.sqlite3") as connection:
        run_id = start_run(connection, "recover", source_root, output_root, "baseline-v2")
        transition_run(connection, run_id, "running")
        pipeline.persist_execution(connection, run_id, execution)
        transition_run(connection, run_id, "completed")
        streams = connection.execute(
            "SELECT stream_index, stream_type, codec, evidence_json FROM media_streams ORDER BY stream_index"
        ).fetchall()
        tool_record = connection.execute(
            "SELECT name, available, evidence_json FROM tool_records WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        output = connection.execute(
            "SELECT output_type, fidelity_grade, validation_state FROM outputs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    assert [(row[0], row[1], row[2]) for row in streams] == [(0, "video", "h264"), (1, "audio", "aac")]
    assert json.loads(streams[0][3])["duration_ms"] == 2000
    assert tool_record[0:2] == ("ffmpeg", 1)
    assert json.loads(tool_record[2])["runs"]
    assert tuple(output) == ("normalized", "validated_normalized", "ffprobe_validated")
