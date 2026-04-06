from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from .constants import EXT_TO_KIND
from .signature_index import detect_anywhere_kind, header_kind_at_byte0, scan_signatures, summarize_signature_hits
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


def build_file_record(root: Path, path: Path, data: bytes) -> FileRecord:
    signature_hits = scan_signatures(data)
    signature_summary = summarize_signature_hits(signature_hits)
    return FileRecord(
        path=path,
        relative_path=path.relative_to(root),
        size=len(data),
        sha256=sha256_bytes(data),
        declared_kind=declared_kind_from_extension(path),
        byte0_kind=header_kind_at_byte0(data),
        anywhere_kind=detect_anywhere_kind(signature_hits),
        signature_summary=signature_summary,
        signature_hits=signature_hits,
    )
