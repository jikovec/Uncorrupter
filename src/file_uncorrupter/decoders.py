from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFile, ImageOps

from .constants import KIND_TO_PIL_FORMAT, VIDEO_OUTPUT_EXT
from .types import Artifact, DecodeResult

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
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def probe_with_pillow(blob: bytes) -> DecodeResult:
    try:
        with Image.open(io.BytesIO(blob)) as img:
            img.load()
            return DecodeResult(
                ok=True,
                decoder="pillow",
                width=img.width,
                height=img.height,
                mode=img.mode,
                decoded_format=str(img.format or ""),
                score=image_entropy(img),
            )
    except Exception as exc:
        return DecodeResult(ok=False, decoder="pillow", error=compact_error(str(exc)))


def save_with_pillow(blob: bytes, output_path: Path, output_kind: str) -> DecodeResult:
    try:
        with Image.open(io.BytesIO(blob)) as img:
            img.load()
            entropy = image_entropy(img)
            img = normalize_for_save(img, output_kind)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_kwargs = {}
            if output_kind == "jpeg":
                save_kwargs = {"quality": 95, "optimize": False}
            elif output_kind == "png":
                save_kwargs = {"optimize": False, "compress_level": 1}
            elif output_kind == "webp":
                save_kwargs = {"quality": 95, "method": 4}
            img.save(output_path, format=KIND_TO_PIL_FORMAT[output_kind], **save_kwargs)
            return DecodeResult(
                ok=True,
                decoder="pillow",
                width=img.width,
                height=img.height,
                mode=img.mode,
                decoded_format=output_kind.upper(),
                score=entropy,
                output_path=output_path,
            )
    except Exception as exc:
        return DecodeResult(ok=False, decoder="pillow", error=compact_error(str(exc)))


def ffmpeg_available() -> bool:
    return FFMPEG_PATH is not None


def ffprobe_available() -> bool:
    return FFPROBE_PATH is not None


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
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=12, check=False)
        except subprocess.TimeoutExpired:
            return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_timeout")
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg", error=compact_error(str(exc)))
        stderr = compact_error(proc.stderr.decode("utf-8", errors="replace"))
        if proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
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
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=12, check=False)
        except subprocess.TimeoutExpired:
            return DecodeResult(ok=False, decoder="ffmpeg", error="ffmpeg_timeout")
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg", error=compact_error(str(exc)))
        stderr = compact_error(proc.stderr.decode("utf-8", errors="replace"))
        if proc.returncode != 0 or not probe_path.exists() or probe_path.stat().st_size == 0:
            return DecodeResult(ok=False, decoder="ffmpeg", error=stderr or "ffmpeg_failed")
        try:
            with Image.open(probe_path) as img:
                img.load()
                entropy = image_entropy(img)
                img = normalize_for_save(img, output_kind)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                save_kwargs = {}
                if output_kind == "jpeg":
                    save_kwargs = {"quality": 95, "optimize": False}
                elif output_kind == "png":
                    save_kwargs = {"optimize": False, "compress_level": 1}
                elif output_kind == "webp":
                    save_kwargs = {"quality": 95, "method": 4}
                img.save(output_path, format=KIND_TO_PIL_FORMAT[output_kind], **save_kwargs)
                return DecodeResult(
                    ok=True,
                    decoder="ffmpeg",
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    decoded_format=output_kind.upper(),
                    score=entropy,
                    output_path=output_path,
                )
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg", error=compact_error(str(exc)))


def probe_video_with_ffmpeg(blob: bytes, input_kind: str) -> DecodeResult:
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
            probe_proc = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12, check=False)
        except subprocess.TimeoutExpired:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffprobe_timeout")
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error=compact_error(str(exc)))

        telemetry: dict[str, object] = {}
        if probe_proc.stdout:
            try:
                telemetry = json.loads(probe_proc.stdout.decode("utf-8", errors="replace"))
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
        try:
            ffmpeg_proc = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20, check=False)
        except subprocess.TimeoutExpired:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffmpeg_timeout", telemetry=telemetry)
        except Exception as exc:
            return DecodeResult(ok=False, decoder="ffmpeg-video", error=compact_error(str(exc)), telemetry=telemetry)

        stderr = compact_error(ffmpeg_proc.stderr.decode("utf-8", errors="replace"))
        if ffmpeg_proc.returncode != 0 or not preview_path.exists() or preview_path.stat().st_size == 0:
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


def recover_video_with_ffmpeg(blob: bytes, input_kind: str, output_path: Path) -> tuple[DecodeResult, list[Artifact]]:
    if not ffmpeg_available() or not ffprobe_available():
        return DecodeResult(ok=False, decoder="ffmpeg-video", error="ffmpeg_or_ffprobe_not_found"), []

    artifacts: list[Artifact] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame_dir = output_path.with_suffix(output_path.suffix + ".frames")
    preview_path = output_path.with_suffix(".preview.png")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{_ffmpeg_suffix(input_kind)}"
        input_path.write_bytes(blob)

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
            str(output_path),
        ]
        remux_proc = subprocess.run(remux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30, check=False)
        remux_error = compact_error(remux_proc.stderr.decode("utf-8", errors="replace"))

        if remux_proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            probe = probe_video_with_ffmpeg(output_path.read_bytes(), output_path.suffix.lstrip(".") or input_kind)
            artifacts.append(
                Artifact(
                    artifact_type="video",
                    path=output_path,
                    sha256=sha256_path(output_path),
                    decoder="ffmpeg-video",
                    width=probe.width,
                    height=probe.height,
                    duration_ms=probe.duration_ms,
                    frame_count=probe.frame_count,
                    meta={"mode": "remux_copy"},
                )
            )

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
            str(preview_path),
        ]
        preview_proc = subprocess.run(preview_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20, check=False)
        preview_error = compact_error(preview_proc.stderr.decode("utf-8", errors="replace"))
        if preview_proc.returncode == 0 and preview_path.exists() and preview_path.stat().st_size > 0:
            with Image.open(preview_path) as img:
                img.load()
                artifacts.append(
                    Artifact(
                        artifact_type="preview_frame",
                        path=preview_path,
                        sha256=sha256_path(preview_path),
                        decoder="ffmpeg-video",
                        width=img.width,
                        height=img.height,
                    )
                )

        if not artifacts:
            frame_dir.mkdir(parents=True, exist_ok=True)
            frame_pattern = frame_dir / "frame_%04d.png"
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
            frames_proc = subprocess.run(frames_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=25, check=False)
            frame_error = compact_error(frames_proc.stderr.decode("utf-8", errors="replace"))
            frame_files = sorted(frame_dir.glob("frame_*.png"))
            if frames_proc.returncode == 0 and frame_files:
                first = frame_files[0]
                with Image.open(first) as img:
                    img.load()
                    artifacts.append(
                        Artifact(
                            artifact_type="frame_set",
                            path=frame_dir,
                            sha256=hashlib.sha256("|".join(p.name for p in frame_files).encode("utf-8")).hexdigest(),
                            decoder="ffmpeg-video",
                            width=img.width,
                            height=img.height,
                            frame_count=len(frame_files),
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


def normalized_video_output_path(output_root: Path, relative_path: Path, family: str) -> Path:
    return output_root / relative_path.with_suffix(VIDEO_OUTPUT_EXT.get(family, ".mkv"))
