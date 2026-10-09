from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Iterable

from .budgets import BudgetTracker, ResourceLimits
from .byte_source import FileByteSource, UnsafeSourceError
from .constants import EXT_TO_KIND
from .signature_index import detect_anywhere_kind, header_kind_at_byte0, scan_signatures, summarize_signature_hits
from .types import FileRecord


def _is_link_or_reparse(path: Path) -> bool:
    try:
        value = os.lstat(path)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, "st_file_attributes", 0) & reparse_flag)


def iter_input_files(root: Path, recursive: bool, all_files: bool) -> Iterable[Path]:
    supplied_root = Path(root)
    if _is_link_or_reparse(supplied_root):
        raise UnsafeSourceError(f"symbolic-link or reparse input roots are not accepted: {root}")
    root = supplied_root.resolve(strict=True)
    if root.is_file():
        paths = [root]
    elif recursive:
        paths = []
        for directory, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
            directory_path = Path(directory)
            directory_names[:] = sorted(
                (name for name in directory_names if not _is_link_or_reparse(directory_path / name)),
                key=str.casefold,
            )
            paths.extend(directory_path / name for name in sorted(file_names, key=str.casefold))
    else:
        paths = sorted(root.glob("*"), key=lambda item: item.as_posix().casefold())
    for path in paths:
        if _is_link_or_reparse(path):
            continue
        try:
            is_file = path.is_file()
        except OSError:
            is_file = True
        if is_file and (all_files or path.suffix.lower() in EXT_TO_KIND):
            yield path


def iter_file_sources(
    root: Path,
    *,
    recursive: bool,
    all_files: bool,
    limits: ResourceLimits | None = None,
) -> Iterable[FileByteSource]:
    limits = limits or ResourceLimits()
    for path in iter_input_files(root, recursive=recursive, all_files=all_files):
        yield FileByteSource(path, limits=limits)


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def declared_kind_from_extension(path: Path) -> str | None:
    return EXT_TO_KIND.get(path.suffix.lower())


def build_file_record(root: Path, path: Path, data: bytes) -> FileRecord:
    signature_hits = scan_signatures(data)
    signature_summary = summarize_signature_hits(signature_hits)
    stat = path.stat()
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
        modified_ns=int(stat.st_mtime_ns),
        device_id=int(stat.st_dev),
        inode_id=int(stat.st_ino),
    )


def build_file_record_from_source(root: Path, source: FileByteSource, *, chunk_size: int = 1 << 20) -> FileRecord:
    digest = hashlib.sha256()
    hits = []
    seen: set[tuple[str, str, int]] = set()
    carry = b""
    processed = 0
    header = b""
    for chunk in source.iter_chunks(chunk_size=chunk_size):
        if not header:
            header = chunk[:8192]
        digest.update(chunk)
        window = carry + chunk
        base = processed - len(carry)
        for hit in scan_signatures(window):
            offset = base + hit.offset
            key = (hit.family, hit.signature_type, offset)
            if key in seen:
                continue
            seen.add(key)
            hit.offset = offset
            hits.append(hit)
        processed += len(chunk)
        carry = window[-128:]
    hits.sort(key=lambda item: (item.offset, -item.confidence, item.family, item.signature_type))
    bounded_hits = []
    counts: dict[tuple[str, str], int] = {}
    for hit in hits:
        key = (hit.family, hit.signature_type)
        if counts.get(key, 0) >= 24:
            continue
        counts[key] = counts.get(key, 0) + 1
        bounded_hits.append(hit)
    relative_root = Path(root).resolve()
    return FileRecord(
        path=source.path,
        relative_path=source.path.relative_to(relative_root) if source.path != relative_root else Path(source.path.name),
        size=source.size,
        sha256=digest.hexdigest(),
        declared_kind=declared_kind_from_extension(source.path),
        byte0_kind=header_kind_at_byte0(header),
        anywhere_kind=detect_anywhere_kind(bounded_hits),
        signature_summary=summarize_signature_hits(bounded_hits),
        signature_hits=bounded_hits,
        modified_ns=source.identity.mtime_ns,
        device_id=source.identity.device,
        inode_id=source.identity.inode,
    )
