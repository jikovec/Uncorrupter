from __future__ import annotations

import io
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFile, ImageOps

from .constants import KIND_TO_PIL_FORMAT
from .types import DecodeResult

ImageFile.LOAD_TRUNCATED_IMAGES = True
FFMPEG_PATH = shutil.which("ffmpeg")


def compact_error(text: str, max_lines: int = 4, max_chars: int = 400) -> str:
    text = (text or "").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""
    normalized = " | ".join(lines[:max_lines])
    if len(normalized) > max_chars:
        normalized = normalized[: max_chars - 3] + "..."
    return normalized


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


def _ffmpeg_suffix(kind: str) -> str:
    return {
        "jpeg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "bmp": ".bmp",
        "tiff": ".tif",
        "webp": ".webp",
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
