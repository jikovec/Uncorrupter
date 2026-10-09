from __future__ import annotations

import hashlib
import io
import json
import math
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageFile, ImageOps

from .atomic import AtomicArtifactWriter, CollisionPolicy
from .budgets import BudgetTracker
from .cancellation import CancellationToken
from .constants import KIND_TO_PIL_FORMAT, VIDEO_OUTPUT_EXT
from .process_runner import IsolationUnavailableError, ProcessPolicy, probe_tool, run_process
from .types import Artifact, DecodeResult, OutcomeGrade

ImageFile.LOAD_TRUNCATED_IMAGES = True
FFMPEG_PATH = shutil.which("ffmpeg")
FFPROBE_PATH = shutil.which("ffprobe")


def compact_error(text: str, max_lines: int = 4, max_chars: int = 400) -> str:
    text = (text or "").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""
    normalized = " | ".join(lines[:max_lines])
    if len(normalized) > max_chars:
        normalized = normalized[: max_chars - 3] + "..."
    return normalized


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_for_save(img: Image.Image, output_kind: str) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if getattr(img, "is_animated", False):
        try:
            img.seek(0)
        except Exception:
            pass

    if output_kind == "jpeg":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return img
    if output_kind == "png":
        if img.mode in ("1", "L", "LA", "P", "RGB", "RGBA"):
            return img
        if img.mode == "CMYK":
            return img.convert("RGB")
        return img.convert("RGBA")
    if output_kind == "gif":
        if img.mode not in ("P", "L"):
            return img.convert("P", palette=Image.ADAPTIVE)
        return img
    if output_kind == "bmp":
        if img.mode not in ("RGB", "L"):
            return img.convert("RGB")
        return img
    if output_kind == "tiff":
        if img.mode in ("1", "L", "LA", "P", "RGB", "RGBA", "CMYK"):
            return img
        return img.convert("RGB")
    if output_kind == "webp":
        if img.mode not in ("RGB", "RGBA", "L"):
            return img.convert("RGBA")
        return img
    return img.convert("RGB")


def image_entropy(img: Image.Image) -> float:
    grayscale = img.convert("L")
    hist = grayscale.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in hist:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def probe_with_pillow(blob: bytes | Path | Any) -> DecodeResult:
    try:
        source = io.BytesIO(blob) if isinstance(blob, bytes) else blob
        with Image.open(source) as img:
            img.load()
            return DecodeResult(
                ok=True,
                decoder="pillow",
                width=img.width,
                height=img.height,
                mode=img.mode,
                decoded_format=str(img.format or ""),
                score=image_entropy(img),
                frame_count=int(getattr(img, "n_frames", 1)),
            )
    except Exception as exc:
        return DecodeResult(ok=False, decoder="pillow", error=compact_error(str(exc)))


def save_with_pillow(
    blob: bytes | Path | Any,
    output_path: Path,
    output_kind: str,
    *,
    collision_policy: CollisionPolicy | str = CollisionPolicy.FAIL,
    budget: BudgetTracker | None = None,
) -> DecodeResult:
    frames: list[Image.Image] = []
    try:
        source = io.BytesIO(blob) if isinstance(blob, bytes) else blob
        with Image.open(source) as img:
            img.load()
            entropy = image_entropy(img)
            frame_total = int(getattr(img, "n_frames", 1))
            save_kwargs = {}
            if output_kind == "jpeg":
                save_kwargs = {"quality": 95, "optimize": False}
            elif output_kind == "png":
                save_kwargs = {"optimize": False, "compress_level": 1}
            elif output_kind == "webp":
                save_kwargs = {"quality": 95, "method": 4}
            with tempfile.TemporaryDirectory(prefix="uncorrupter-image-") as directory:
                encoded_path = Path(directory) / f"encoded{output_path.suffix or '.bin'}"
                if frame_total > 1 and output_kind in {"gif", "tiff", "webp"}:
                    durations = []
                    for index in range(frame_total):
                        img.seek(index)
                        frame = normalize_for_save(img.copy(), output_kind)
                        frames.append(frame)
                        durations.append(int(img.info.get("duration", 0)))
                    animated_kwargs = dict(save_kwargs)
                    animated_kwargs.update({"save_all": True, "append_images": frames[1:]})
                    if any(durations):
                        animated_kwargs["duration"] = durations
                    if "loop" in img.info:
                        animated_kwargs["loop"] = int(img.info["loop"])
                    frames[0].save(encoded_path, format=KIND_TO_PIL_FORMAT[output_kind], **animated_kwargs)
                    saved_image = frames[0]
                else:
                    saved_image = normalize_for_save(img, output_kind)
                    saved_image.save(encoded_path, format=KIND_TO_PIL_FORMAT[output_kind], **save_kwargs)
                validated = probe_with_pillow(encoded_path)
                if not validated.ok:
                    return DecodeResult(ok=False, decoder="pillow", error=f"encoded_validation_failed:{validated.error}")
                published = AtomicArtifactWriter(
                    output_path.parent,
                    collision_policy=collision_policy,
                    budget=budget,
                ).publish_stream(
                    output_path.name,
                    _file_chunks(encoded_path),
                    validator=lambda path: probe_with_pillow(path).ok,
                )
                return DecodeResult(
                    ok=True,
                    decoder="pillow",
                    width=saved_image.width,
                    height=saved_image.height,
                    mode=saved_image.mode,
                    decoded_format=output_kind.upper(),
                    score=entropy,
                    output_path=published.path,
                    frame_count=frame_total,
                )
    except Exception as exc:
        return DecodeResult(ok=False, decoder="pillow", error=compact_error(str(exc)))
    finally:
        for frame in frames:
            frame.close()


def ffmpeg_available() -> bool:
    return FFMPEG_PATH is not None and os.environ.get("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "").lower() not in {"1", "true", "yes", "on"}


def ffprobe_available() -> bool:
    return FFPROBE_PATH is not None and os.environ.get("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "").lower() not in {"1", "true", "yes", "on"}


def _run_media_tool(
    command: list[str],
    *,
    timeout: float,
    cancellation: CancellationToken | None = None,
) -> tuple[int | None, bytes, bool, bool]:
    try:
        result = run_process(
            command,
            ProcessPolicy(timeout_seconds=timeout, max_output_bytes=1 << 20),
            cancellation=cancellation,
        )
    except IsolationUnavailableError:
        return None, b"external_tools_disabled", False, False
    return result.returncode, result.stderr, result.timed_out, result.cancelled


def _ffmpeg_suffix(kind: str) -> str:
    return {
        "jpeg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "bmp": ".bmp",
        "tiff": ".tif",
        "webp": ".webp",
        "mp4": ".mp4",
        "mov": ".mov",
        "avi": ".avi",
        "mkv": ".mkv",
        "webm": ".webm",
        "mpegts": ".ts",
        "mpegps": ".mpg",
        "flv": ".flv",
        "asf": ".asf",
        "wmv": ".wmv",
    }.get(kind, ".bin")


def probe_with_ffmpeg(blob: bytes, input_kind: str) -> DecodeResult:
    if not ffmpeg_available():
        return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_not_found")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{_ffmpeg_suffix(input_kind)}"
        output_path = tmpdir_path / "probe.png"
        input_path.write_bytes(blob)
        cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-frames:v", "1",
            str(output_path),
        ]
        returncode, stderr_bytes, timed_out, cancelled = _run_media_tool(cmd, timeout=12)
        if timed_out:
            return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_timeout")
        if cancelled:
            return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_cancelled")
        stderr = compact_error(stderr_bytes.decode("utf-8", errors="replace"))
        if returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
            return DecodeResult(ok=False, decoder="ffmpeg", error=stderr or "ffmpeg_failed")
        try:
            with Image.open(output_path) as img:
                img.load()
                return DecodeResult(
                    ok=True,
                    decoder="ffmpeg",
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    decoded_format="PNG",
                    score=image_entropy(img),
                )
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg", error=compact_error(str(exc)))


def save_with_ffmpeg(blob: bytes, input_kind: str, output_path: Path, output_kind: str) -> DecodeResult:
    if not ffmpeg_available():
        return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_not_found")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{_ffmpeg_suffix(input_kind)}"
        probe_path = tmpdir_path / "decoded.png"
        input_path.write_bytes(blob)
        cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-frames:v", "1",
            str(probe_path),
        ]
        returncode, stderr_bytes, timed_out, cancelled = _run_media_tool(cmd, timeout=12)
        if timed_out:
            return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_timeout")
        if cancelled:
            return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_cancelled")
        stderr = compact_error(stderr_bytes.decode("utf-8", errors="replace"))
        if returncode != 0 or not probe_path.exists() or probe_path.stat().st_size == 0:
            return DecodeResult(ok=False, decoder="ffmpeg", error=stderr or "ffmpeg_failed")
        try:
            with Image.open(probe_path) as img:
                img.load()
                entropy = image_entropy(img)
                img = normalize_for_save(img, output_kind)
                final = save_with_pillow(probe_path.read_bytes(), output_path, output_kind)
                if not final.ok:
                    return final
                return DecodeResult(
                    ok=True,
                    decoder="ffmpeg",
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    decoded_format=output_kind.upper(),
                    score=entropy,
                    output_path=final.output_path,
                )
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg", error=compact_error(str(exc)))


def probe_video_with_ffmpeg(
    blob: bytes,
    input_kind: str,
    *,
    cancellation: CancellationToken | None = None,
) -> DecodeResult:
    if not ffmpeg_available() or not ffprobe_available():
        return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffmpeg_or_ffprobe_not_found")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{_ffmpeg_suffix(input_kind)}"
        preview_path = tmpdir_path / "preview.png"
        input_path.write_bytes(blob)

        probe_cmd = [
            FFPROBE_PATH,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(input_path),
        ]
        try:
            probe_result = run_process(
                probe_cmd,
                ProcessPolicy(timeout_seconds=12, max_output_bytes=1 << 20),
                cancellation=cancellation,
            )
        except IsolationUnavailableError:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="external_tools_disabled")
        if probe_result.timed_out:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffprobe_timeout")
        if probe_result.cancelled:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffprobe_cancelled")

        telemetry: dict[str, object] = {}
        if probe_result.stdout:
            try:
                telemetry = json.loads(probe_result.stdout.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                telemetry = {}

        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-frames:v", "1",
            str(preview_path),
        ]
        returncode, stderr_bytes, timed_out, cancelled = _run_media_tool(
            ffmpeg_cmd,
            timeout=20,
            cancellation=cancellation,
        )
        if timed_out:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffmpeg_timeout", telemetry=telemetry)
        if cancelled:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffmpeg_cancelled", telemetry=telemetry)

        stderr = compact_error(stderr_bytes.decode("utf-8", errors="replace"))
        if returncode != 0 or not preview_path.exists() or preview_path.stat().st_size == 0:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error=stderr or "ffmpeg_failed", telemetry=telemetry)

        width = 0
        height = 0
        try:
            with Image.open(preview_path) as img:
                img.load()
                width, height = img.width, img.height
        except Exception:
            pass

        streams = telemetry.get("streams") or []
        format_info = telemetry.get("format") or {}
        duration_ms = 0
        frame_count = 0
        for stream in streams:
            if stream.get("codec_type") == "video":
                width = int(stream.get("width") or width or 0)
                height = int(stream.get("height") or height or 0)
                frame_count = max(frame_count, int(float(stream.get("nb_frames") or 0) if str(stream.get("nb_frames") or "").replace('.', '', 1).isdigit() else 0))
        duration = format_info.get("duration")
        try:
            duration_ms = int(float(duration) * 1000) if duration is not None else 0
        except (TypeError, ValueError):
            duration_ms = 0

        score = (width * height) / 5000.0 + min(duration_ms / 1000.0, 300.0) + (20.0 if frame_count > 0 else 0.0)
        return DecodeResult(
            ok=True,
            decoder="ffmpeg-video",
            width=width,
            height=height,
            decoded_format=str(format_info.get("format_name") or input_kind),
            score=score,
            duration_ms=duration_ms,
            frame_count=frame_count,
            telemetry=telemetry,
        )


def _process_evidence(operation: str, result: Any) -> dict[str, Any]:
    return {
        "operation": operation,
        "exit_code": result.returncode,
        "timed_out": result.timed_out,
        "cancelled": result.cancelled,
        "duration_seconds": round(float(result.duration_seconds), 6),
        "stdout_sha256": result.stdout_sha256,
        "stderr_sha256": result.stderr_sha256,
        "output_truncated": result.output_truncated,
        "cleanup_ok": result.cleanup_ok,
    }


def _safe_int(value: object) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _duration_ms(value: object) -> int:
    try:
        return max(0, int(float(str(value)) * 1000))
    except (TypeError, ValueError, OverflowError):
        return 0


def _normalized_streams(payload: dict[str, Any]) -> list[dict[str, Any]]:
    streams: list[dict[str, Any]] = []
    format_payload = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    format_duration = _duration_ms(format_payload.get("duration"))
    for position, raw in enumerate(payload.get("streams") or []):
        if not isinstance(raw, dict):
            continue
        tags = raw.get("tags") if isinstance(raw.get("tags"), dict) else {}
        disposition = raw.get("disposition") if isinstance(raw.get("disposition"), dict) else {}
        duration = _duration_ms(raw.get("duration")) or format_duration
        streams.append(
            {
                "index": _safe_int(raw.get("index", position)),
                "type": str(raw.get("codec_type") or "unknown"),
                "codec": str(raw.get("codec_name") or "unknown"),
                "codec_long_name": str(raw.get("codec_long_name") or "")[:200],
                "profile": str(raw.get("profile") or "")[:100],
                "width": _safe_int(raw.get("width")),
                "height": _safe_int(raw.get("height")),
                "duration_ms": duration,
                "frames": _safe_int(raw.get("nb_frames")),
                "channels": _safe_int(raw.get("channels")),
                "sample_rate": _safe_int(raw.get("sample_rate")),
                "language": str(tags.get("language") or "")[:40],
                "default": bool(disposition.get("default", 0)),
                "forced": bool(disposition.get("forced", 0)),
            }
        )
    return streams


def _format_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    return {
        "format_name": str(raw.get("format_name") or "")[:200],
        "format_long_name": str(raw.get("format_long_name") or "")[:200],
        "duration_ms": _duration_ms(raw.get("duration")),
        "size": _safe_int(raw.get("size")),
        "bit_rate": _safe_int(raw.get("bit_rate")),
    }


def _probe_media_path(
    path: Path,
    *,
    cancellation: CancellationToken | None,
    timeout_seconds: float,
    max_tool_output_bytes: int,
    operation: str,
) -> tuple[bool, dict[str, Any], dict[str, Any], str]:
    if FFPROBE_PATH is None:
        return False, {}, {}, "ffprobe_not_found"
    try:
        result = run_process(
            [
                FFPROBE_PATH,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            ProcessPolicy(timeout_seconds=timeout_seconds, max_output_bytes=max_tool_output_bytes),
            cancellation=cancellation,
        )
    except IsolationUnavailableError as exc:
        return False, {}, {}, compact_error(str(exc)) or "external_tools_disabled"
    evidence = _process_evidence(operation, result)
    if result.cancelled and cancellation is not None:
        cancellation.checkpoint()
    if result.timed_out:
        return False, {}, evidence, "ffprobe_timeout"
    if result.returncode != 0:
        error = compact_error(result.stderr.decode("utf-8", errors="replace"))
        return False, {}, evidence, error or f"ffprobe_exit_{result.returncode}"
    try:
        payload = json.loads(result.stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, {}, evidence, "ffprobe_invalid_json"
    if not isinstance(payload, dict):
        return False, {}, evidence, "ffprobe_invalid_payload"
    normalized = {
        "streams": _normalized_streams(payload),
        "format": _format_evidence(payload),
    }
    if not normalized["streams"]:
        return False, normalized, evidence, "ffprobe_no_streams"
    return True, normalized, evidence, ""


def _run_ffmpeg_goal(
    command: list[str],
    *,
    cancellation: CancellationToken | None,
    timeout_seconds: float,
    max_tool_output_bytes: int,
    operation: str,
) -> tuple[bool, dict[str, Any], str]:
    try:
        result = run_process(
            command,
            ProcessPolicy(timeout_seconds=timeout_seconds, max_output_bytes=max_tool_output_bytes),
            cancellation=cancellation,
        )
    except IsolationUnavailableError as exc:
        return False, {}, compact_error(str(exc)) or "external_tools_disabled"
    evidence = _process_evidence(operation, result)
    if result.cancelled and cancellation is not None:
        cancellation.checkpoint()
    if result.timed_out:
        return False, evidence, "ffmpeg_timeout"
    if result.returncode != 0:
        error = compact_error(result.stderr.decode("utf-8", errors="replace"))
        return False, evidence, error or f"ffmpeg_exit_{result.returncode}"
    return True, evidence, ""


def _media_tool_identity(cancellation: CancellationToken | None) -> dict[str, Any]:
    ffmpeg = probe_tool(
        str(FFMPEG_PATH or "ffmpeg"),
        version_args=("-version",),
        policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=64 * 1024),
        cancellation=cancellation,
    )
    ffprobe = probe_tool(
        str(FFPROBE_PATH or "ffprobe"),
        version_args=("-version",),
        policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=64 * 1024),
        cancellation=cancellation,
    )
    if cancellation is not None:
        cancellation.checkpoint()
    available = ffmpeg.available and ffprobe.available
    return {
        "name": "ffmpeg",
        "available": available,
        "resolved_path": ffmpeg.resolved_path,
        "version": ffmpeg.version,
        "policy_id": "bounded-v1",
        "ffprobe": {
            "available": ffprobe.available,
            "resolved_path": ffprobe.resolved_path,
            "version": ffprobe.version,
            "error": ffprobe.error,
        },
        "error": None if available else ffmpeg.error or ffprobe.error or "ffmpeg_or_ffprobe_not_found",
        "runs": [],
    }


def _media_dimensions(streams: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    videos = [stream for stream in streams if stream.get("type") == "video"]
    if not videos:
        duration = max((_safe_int(stream.get("duration_ms")) for stream in streams), default=0)
        return 0, 0, duration, 0
    stream = videos[0]
    duration = max((_safe_int(item.get("duration_ms")) for item in streams), default=0)
    frames = max((_safe_int(item.get("frames")) for item in videos), default=0)
    return _safe_int(stream.get("width")), _safe_int(stream.get("height")), duration, frames


def _tool_artifact_limit(
    budget: BudgetTracker | None,
    max_tool_artifact_bytes: int,
) -> int:
    limit = max_tool_artifact_bytes
    if budget is not None:
        budget.check("output_bytes", 1)
        limit = min(limit, int(budget.remaining("output_bytes")))
    return max(1, int(limit))


def recover_media_goal_with_ffmpeg(
    blob: bytes | Path,
    input_kind: str,
    output_root: Path,
    goal: str,
    *,
    budget: BudgetTracker | None = None,
    cancellation: CancellationToken | None = None,
    timeout_seconds: float = 30.0,
    max_tool_output_bytes: int = 1 << 20,
    max_tool_artifact_bytes: int = 256 * (1 << 20),
    max_streams: int = 64,
    input_offset: int = 0,
) -> tuple[DecodeResult, list[Artifact]]:
    """Execute one explicit FFmpeg media goal and validate every published byte stream."""
    if goal not in {"normalize", "extract", "preview"}:
        return DecodeResult(ok=False, decoder="ffmpeg-media", error=f"unsupported_media_goal:{goal}"), []
    if not ffmpeg_available() or not ffprobe_available():
        return DecodeResult(ok=False, decoder="ffmpeg-media", error="ffmpeg_or_ffprobe_not_found"), []

    cancellation = cancellation or CancellationToken()
    cancellation.checkpoint()
    tool = _media_tool_identity(cancellation)
    if not tool["available"]:
        return DecodeResult(
            ok=False,
            decoder="ffmpeg-media",
            error=str(tool["error"] or "ffmpeg_or_ffprobe_not_found"),
            telemetry={"tool": tool, "streams": []},
        ), []

    writer = AtomicArtifactWriter(output_root, budget=budget)
    artifact_limit = _tool_artifact_limit(budget, max_tool_artifact_bytes)
    artifacts: list[Artifact] = []
    warnings: list[str] = []

    with tempfile.TemporaryDirectory(prefix="uncorrupter-media-") as directory:
        root = Path(directory)
        if isinstance(blob, Path):
            source_path = blob.resolve(strict=True)
            if input_offset < 0 or input_offset > source_path.stat().st_size:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error="invalid_media_input_offset"), []
            if input_offset:
                input_path = root / f"input{_ffmpeg_suffix(input_kind)}"
                with source_path.open("rb") as source_handle, input_path.open("xb") as target_handle:
                    source_handle.seek(input_offset)
                    shutil.copyfileobj(source_handle, target_handle, length=1 << 20)
            else:
                input_path = source_path
        else:
            if input_offset:
                blob = blob[input_offset:]
            input_path = root / f"input{_ffmpeg_suffix(input_kind)}"
            input_path.write_bytes(blob)
        input_ok, input_probe, probe_evidence, probe_error = _probe_media_path(
            input_path,
            cancellation=cancellation,
            timeout_seconds=min(timeout_seconds, 15.0),
            max_tool_output_bytes=max_tool_output_bytes,
            operation="probe_input",
        )
        if probe_evidence:
            tool["runs"].append(probe_evidence)
        if not input_ok:
            return DecodeResult(
                ok=False,
                decoder="ffmpeg-media",
                error=probe_error or "input_probe_failed",
                telemetry={"tool": tool, "streams": input_probe.get("streams", [])},
            ), []

        source_streams = list(input_probe["streams"])
        width, height, duration_ms, frame_count = _media_dimensions(source_streams)
        format_info = dict(input_probe["format"])
        decoded_coverage: dict[str, Any]

        if goal == "normalize":
            has_video = any(stream["type"] == "video" for stream in source_streams)
            extension = ".mkv" if has_video else ".mka"
            media_type = "video/x-matroska" if has_video else "audio/x-matroska"
            output_temp = root / f"normalized{extension}"
            command = [
                str(FFMPEG_PATH),
                "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-err_detect", "ignore_err", "-fflags", "+discardcorrupt",
                "-i", str(input_path),
                "-map", "0", "-c", "copy", "-fs", str(artifact_limit),
                str(output_temp),
            ]
            converted, run_evidence, error = _run_ffmpeg_goal(
                command,
                cancellation=cancellation,
                timeout_seconds=timeout_seconds,
                max_tool_output_bytes=max_tool_output_bytes,
                operation="normalize",
            )
            if run_evidence:
                tool["runs"].append(run_evidence)
            if not converted or not output_temp.is_file() or output_temp.stat().st_size <= 0:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error=error or "normalize_output_missing", telemetry={"tool": tool, "streams": source_streams}), []
            if output_temp.stat().st_size > artifact_limit:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error="normalize_output_limit_exceeded", telemetry={"tool": tool, "streams": source_streams}), []
            output_ok, output_probe, validation_evidence, validation_error = _probe_media_path(
                output_temp,
                cancellation=cancellation,
                timeout_seconds=min(timeout_seconds, 15.0),
                max_tool_output_bytes=max_tool_output_bytes,
                operation="validate_normalized",
            )
            if validation_evidence:
                tool["runs"].append(validation_evidence)
            if not output_ok:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error=validation_error or "normalize_validation_failed", telemetry={"tool": tool, "streams": source_streams}), []

            output_streams = list(output_probe["streams"])
            expected = Counter(stream["type"] for stream in source_streams)
            observed = Counter(stream["type"] for stream in output_streams)
            matched = sum(min(count, observed.get(kind, 0)) for kind, count in expected.items())
            coverage = matched / len(source_streams) if source_streams else 0.0
            decoded_coverage = {
                "mode": "stream_type_preservation",
                "source_streams": len(source_streams),
                "validated_output_streams": len(output_streams),
                "matched_streams": matched,
                "fraction": round(coverage, 6),
            }
            grade = OutcomeGrade.VALIDATED_NORMALIZED.value if coverage == 1.0 else OutcomeGrade.PARTIAL_CONTENT.value
            if coverage < 1.0:
                warnings.append("normalized output did not preserve every declared stream type")
            validated_sha256 = sha256_path(output_temp)
            published = writer.publish_stream(output_temp.name, _file_chunks(output_temp))
            if published.sha256 != validated_sha256:
                raise RuntimeError("published normalized bytes differ from the validated tool output")
            artifacts.append(
                Artifact(
                    artifact_type="normalized",
                    path=published.path,
                    sha256=published.sha256,
                    decoder="ffmpeg-media",
                    width=width,
                    height=height,
                    duration_ms=duration_ms,
                    frame_count=frame_count,
                    size=published.size,
                    media_type=media_type,
                    fidelity_grade=grade,
                    validation_state="ffprobe_validated",
                    validators=[{"name": "ffprobe", "state": "passed", "validated_sha256": validated_sha256}],
                    published=True,
                    meta={"mode": "remux_copy", "atomic": published.atomic, "decoded_coverage": decoded_coverage},
                )
            )

        elif goal == "extract":
            supported = [stream for stream in source_streams if stream["type"] in {"video", "audio", "subtitle"}]
            if len(supported) > max_streams:
                warnings.append(f"stream extraction limited to {max_streams} of {len(supported)} supported streams")
                supported = supported[:max_streams]
            for stream in supported:
                cancellation.checkpoint()
                stream_limit = _tool_artifact_limit(budget, max_tool_artifact_bytes)
                stream_type = str(stream["type"])
                stream_index = int(stream["index"])
                extension = {"video": ".mkv", "audio": ".mka", "subtitle": ".mks"}[stream_type]
                media_type = {
                    "video": "video/x-matroska",
                    "audio": "audio/x-matroska",
                    "subtitle": "application/x-matroska",
                }[stream_type]
                output_temp = root / f"stream-{stream_index:03d}-{stream_type}{extension}"
                command = [
                    str(FFMPEG_PATH),
                    "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-err_detect", "ignore_err", "-fflags", "+discardcorrupt",
                    "-i", str(input_path),
                    "-map", f"0:{stream_index}", "-c", "copy", "-fs", str(stream_limit),
                    str(output_temp),
                ]
                converted, run_evidence, error = _run_ffmpeg_goal(
                    command,
                    cancellation=cancellation,
                    timeout_seconds=timeout_seconds,
                    max_tool_output_bytes=max_tool_output_bytes,
                    operation=f"extract_stream_{stream_index}",
                )
                if run_evidence:
                    tool["runs"].append(run_evidence)
                if not converted or not output_temp.is_file() or output_temp.stat().st_size <= 0:
                    warnings.append(f"stream {stream_index} extraction failed: {error or 'output_missing'}")
                    continue
                if output_temp.stat().st_size > stream_limit:
                    warnings.append(f"stream {stream_index} extraction exceeded the output limit")
                    continue
                output_ok, output_probe, validation_evidence, validation_error = _probe_media_path(
                    output_temp,
                    cancellation=cancellation,
                    timeout_seconds=min(timeout_seconds, 15.0),
                    max_tool_output_bytes=max_tool_output_bytes,
                    operation=f"validate_stream_{stream_index}",
                )
                if validation_evidence:
                    tool["runs"].append(validation_evidence)
                output_streams = list(output_probe.get("streams", []))
                if not output_ok or not any(item["type"] == stream_type for item in output_streams):
                    warnings.append(f"stream {stream_index} validation failed: {validation_error or 'type_mismatch'}")
                    continue
                validated_sha256 = sha256_path(output_temp)
                published = writer.publish_stream(output_temp.name, _file_chunks(output_temp))
                if published.sha256 != validated_sha256:
                    raise RuntimeError(f"published stream {stream_index} differs from the validated tool output")
                output_width, output_height, output_duration, output_frames = _media_dimensions(output_streams)
                artifacts.append(
                    Artifact(
                        artifact_type="extracted",
                        path=published.path,
                        sha256=published.sha256,
                        decoder="ffmpeg-media",
                        width=output_width,
                        height=output_height,
                        duration_ms=output_duration,
                        frame_count=output_frames,
                        size=published.size,
                        media_type=media_type,
                        fidelity_grade=OutcomeGrade.PARTIAL_CONTENT.value,
                        validation_state="ffprobe_validated",
                        validators=[{"name": "ffprobe", "state": "passed", "validated_sha256": validated_sha256}],
                        published=True,
                        meta={"source_stream": stream, "atomic": published.atomic},
                    )
                )
            decoded_coverage = {
                "mode": "supported_stream_extraction",
                "supported_streams": len(supported),
                "validated_outputs": len(artifacts),
                "fraction": round(len(artifacts) / len(supported), 6) if supported else 0.0,
            }
            grade = OutcomeGrade.PARTIAL_CONTENT.value
            if not artifacts:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error="no_supported_stream_was_extracted", telemetry={"tool": tool, "streams": source_streams, "warnings": warnings, "decoded_coverage": decoded_coverage}), []

        else:
            video_streams = [stream for stream in source_streams if stream["type"] == "video"]
            if not video_streams:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error="preview_requires_video_stream", telemetry={"tool": tool, "streams": source_streams}), []
            selected = video_streams[0]
            output_temp = root / "preview.png"
            command = [
                str(FFMPEG_PATH),
                "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-err_detect", "ignore_err", "-fflags", "+discardcorrupt",
                "-i", str(input_path),
                "-map", f"0:{int(selected['index'])}", "-frames:v", "1",
                str(output_temp),
            ]
            converted, run_evidence, error = _run_ffmpeg_goal(
                command,
                cancellation=cancellation,
                timeout_seconds=timeout_seconds,
                max_tool_output_bytes=max_tool_output_bytes,
                operation="preview",
            )
            if run_evidence:
                tool["runs"].append(run_evidence)
            if not converted or not output_temp.is_file() or output_temp.stat().st_size <= 0:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error=error or "preview_output_missing", telemetry={"tool": tool, "streams": source_streams}), []
            if output_temp.stat().st_size > artifact_limit:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error="preview_output_limit_exceeded", telemetry={"tool": tool, "streams": source_streams}), []
            try:
                with Image.open(output_temp) as image:
                    image.load()
                    width, height = image.width, image.height
            except Exception as exc:
                return DecodeResult(ok=False, decoder="ffmpeg-media", error=f"preview_validation_failed:{compact_error(str(exc))}", telemetry={"tool": tool, "streams": source_streams}), []
            validated_sha256 = sha256_path(output_temp)
            published = writer.publish_stream(output_temp.name, _file_chunks(output_temp))
            if published.sha256 != validated_sha256:
                raise RuntimeError("published preview bytes differ from the validated tool output")
            decoded_coverage = {
                "mode": "single_frame_preview",
                "source_video_stream": int(selected["index"]),
                "validated_frames": 1,
                "fraction": None,
            }
            grade = OutcomeGrade.PREVIEW_ONLY.value
            artifacts.append(
                Artifact(
                    artifact_type="preview",
                    path=published.path,
                    sha256=published.sha256,
                    decoder="ffmpeg-media",
                    width=width,
                    height=height,
                    duration_ms=0,
                    frame_count=1,
                    size=published.size,
                    media_type="image/png",
                    fidelity_grade=grade,
                    validation_state="pillow_validated",
                    validators=[{"name": "Pillow", "state": "passed", "validated_sha256": validated_sha256}],
                    published=True,
                    meta={"source_stream": selected, "atomic": published.atomic},
                )
            )

    tool["duration_seconds"] = round(sum(float(item.get("duration_seconds") or 0.0) for item in tool["runs"]), 6)
    telemetry = {
        "goal": goal,
        "streams": source_streams,
        "format": format_info,
        "decoded_coverage": decoded_coverage,
        "warnings": warnings,
        "tool": tool,
        "fidelity_grade": grade,
    }
    return DecodeResult(
        ok=True,
        decoder="ffmpeg-media",
        width=width,
        height=height,
        decoded_format=str(format_info.get("format_name") or input_kind),
        output_path=artifacts[0].path if artifacts else None,
        duration_ms=duration_ms,
        frame_count=frame_count if goal != "preview" else 1,
        score=(width * height) / 5000.0 + min(duration_ms / 1000.0, 300.0) + len(artifacts) * 3.0,
        telemetry=telemetry,
    ), artifacts


def recover_video_with_ffmpeg(blob: bytes, input_kind: str, output_path: Path) -> tuple[DecodeResult, list[Artifact]]:
    if not ffmpeg_available() or not ffprobe_available():
        return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffmpeg_or_ffprobe_not_found"), []

    artifacts: list[Artifact] = []
    frame_dir = output_path.with_suffix(output_path.suffix + ".frames")
    preview_path = output_path.with_suffix(".preview.png")
    writer = AtomicArtifactWriter(output_path.parent)
    initial_probe = probe_video_with_ffmpeg(blob, input_kind)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{_ffmpeg_suffix(input_kind)}"
        input_path.write_bytes(blob)
        remux_path = tmpdir_path / f"recovered{output_path.suffix}"

        remux_cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-map", "0",
            "-c", "copy",
            str(remux_path),
        ]
        remux_code, remux_stderr, remux_timeout, _ = _run_media_tool(remux_cmd, timeout=30)
        remux_error = "ffmpeg_timeout" if remux_timeout else compact_error(remux_stderr.decode("utf-8", errors="replace"))

        if remux_code == 0 and remux_path.exists() and remux_path.stat().st_size > 0:
            try:
                published = writer.publish_stream(output_path.name, _file_chunks(remux_path))
                artifacts.append(
                    Artifact(
                        artifact_type="video",
                        path=published.path,
                        sha256=published.sha256,
                        decoder="ffmpeg-video",
                        width=initial_probe.width,
                        height=initial_probe.height,
                        duration_ms=initial_probe.duration_ms,
                        frame_count=initial_probe.frame_count,
                        size=published.size,
                        media_type=f"video/{output_path.suffix.lstrip('.') or input_kind}",
                        fidelity_grade="validated_normalized",
                        validation_state="decoder_validated",
                        published=True,
                        meta={"mode": "remux_copy", "atomic": published.atomic},
                    )
                )
            except Exception as exc:
                remux_error = compact_error(str(exc))

        preview_temp = tmpdir_path / "preview.png"
        preview_cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-frames:v", "1",
            str(preview_temp),
        ]
        preview_code, preview_stderr, preview_timeout, _ = _run_media_tool(preview_cmd, timeout=20)
        preview_error = "ffmpeg_timeout" if preview_timeout else compact_error(preview_stderr.decode("utf-8", errors="replace"))
        if preview_code == 0 and preview_temp.exists() and preview_temp.stat().st_size > 0:
            with Image.open(preview_temp) as img:
                img.load()
                try:
                    published = writer.publish_stream(preview_path.name, _file_chunks(preview_temp))
                    artifacts.append(
                        Artifact(
                            artifact_type="preview_frame",
                            path=published.path,
                            sha256=published.sha256,
                            decoder="ffmpeg-video",
                            width=img.width,
                            height=img.height,
                            size=published.size,
                            media_type="image/png",
                            fidelity_grade="preview_only",
                            validation_state="decoder_validated",
                            published=True,
                            meta={"atomic": published.atomic},
                        )
                    )
                except Exception as exc:
                    preview_error = compact_error(str(exc))

        if not artifacts:
            temp_frames = tmpdir_path / "frames"
            temp_frames.mkdir()
            frame_pattern = temp_frames / "frame_%04d.png"
            frames_cmd = [
                FFMPEG_PATH,
                "-nostdin",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-err_detect", "ignore_err",
                "-fflags", "+discardcorrupt",
                "-i", str(input_path),
                "-vsync", "0",
                "-frames:v", "8",
                str(frame_pattern),
            ]
            frames_code, frames_stderr, frames_timeout, _ = _run_media_tool(frames_cmd, timeout=25)
            frame_error = "ffmpeg_timeout" if frames_timeout else compact_error(frames_stderr.decode("utf-8", errors="replace"))
            frame_files = sorted(temp_frames.glob("frame_*.png"))
            if frames_code == 0 and frame_files:
                first = frame_files[0]
                with Image.open(first) as img:
                    img.load()
                    published_frames = []
                    for frame_file in frame_files:
                        published_frames.append(
                            writer.publish_stream(Path(frame_dir.name) / frame_file.name, _file_chunks(frame_file))
                        )
                    artifacts.append(
                        Artifact(
                            artifact_type="frame_set",
                            path=frame_dir,
                            sha256=hashlib.sha256("|".join(item.sha256 for item in published_frames).encode("ascii")).hexdigest(),
                            decoder="ffmpeg-video",
                            width=img.width,
                            height=img.height,
                            frame_count=len(frame_files),
                            size=sum(item.size for item in published_frames),
                            media_type="image/png",
                            fidelity_grade="preview_only",
                            validation_state="decoder_validated",
                            published=True,
                        )
                    )
            else:
                return (
                    DecodeResult(ok=False, decoder="ffmpeg-video", error=frame_error or preview_error or remux_error or "ffmpeg_failed"),
                    [],
                )

    primary = next((artifact for artifact in artifacts if artifact.artifact_type == "video"), None)
    preview = next((artifact for artifact in artifacts if artifact.artifact_type in {"preview_frame", "frame_set"}), None)
    chosen = primary or preview
    if chosen is None:
        return DecodeResult(ok=False, decoder="ffmpeg-video", error="no_video_artifacts"), []

    return (
        DecodeResult(
            ok=True,
            decoder="ffmpeg-video",
            width=chosen.width,
            height=chosen.height,
            decoded_format=input_kind,
            output_path=primary.path if primary else chosen.path,
            duration_ms=primary.duration_ms if primary else 0,
            frame_count=primary.frame_count if primary else chosen.frame_count,
            score=(chosen.width * chosen.height) / 5000.0 + min((primary.duration_ms if primary else 0) / 1000.0, 300.0) + chosen.frame_count * 3.0,
        ),
        artifacts,
    )


def _file_chunks(path: Path, *, chunk_size: int = 1 << 20):
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


def normalized_video_output_path(output_root: Path, relative_path: Path, family: str) -> Path:
    return output_root / relative_path.with_suffix(VIDEO_OUTPUT_EXT.get(family, ".mkv"))
