from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from .constants import BMP_SIG, EXT_TO_KIND, GIF87A, GIF89A, PNG_SIG, RIFF, TIFF_BE, TIFF_LE, WEBP, SOI
from .types import FileRecord


def iter_input_files(root: Path, recursive: bool, all_files: bool) -> Iterable[Path]:
    iterator = root.rglob("*") if recursive else root.glob("*")
    for path in iterator:
        if not path.is_file():
            continue
        if all_files or path.suffix.lower() in EXT_TO_KIND:
            yield path


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def declared_kind_from_extension(path: Path) -> str | None:
    return EXT_TO_KIND.get(path.suffix.lower())


def header_kind_at_byte0(data: bytes) -> str:
    if data.startswith(SOI):
        return "jpeg"
    if data.startswith(PNG_SIG):
        return "png"
    if data.startswith(GIF87A) or data.startswith(GIF89A):
        return "gif"
    if data.startswith(BMP_SIG):
        return "bmp"
    if data.startswith(TIFF_LE) or data.startswith(TIFF_BE):
        return "tiff"
    if data.startswith(RIFF) and len(data) >= 12 and data[8:12] == WEBP:
        return "webp"
    return "unknown"


def build_file_record(root: Path, path: Path, data: bytes) -> FileRecord:
    return FileRecord(
        path=path,
        relative_path=path.relative_to(root),
        size=len(data),
        sha256=sha256_bytes(data),
        declared_kind=declared_kind_from_extension(path),
        byte0_kind=header_kind_at_byte0(data),
    )
