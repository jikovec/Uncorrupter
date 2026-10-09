from __future__ import annotations

import hashlib
import io
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator

from .budgets import BudgetExceeded, BudgetTracker, ResourceLimits


class SourceChangedError(RuntimeError):
    pass


class UnsafeSourceError(RuntimeError):
    pass


class SourceReader(io.RawIOBase):
    """Read-only seekable view over an immutable :class:`FileByteSource`.

    Standard-library parsers such as ``zipfile`` and Pillow can consume this
    adapter without forcing the complete source into one ``bytes`` object.
    Every read still passes through the source identity and scan-budget checks.
    """

    def __init__(self, source: FileByteSource) -> None:
        super().__init__()
        self._source = source
        self._position = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def tell(self) -> int:
        self._checkClosed()
        return self._position

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        self._checkClosed()
        if whence == os.SEEK_SET:
            position = offset
        elif whence == os.SEEK_CUR:
            position = self._position + offset
        elif whence == os.SEEK_END:
            position = self._source.size + offset
        else:
            raise ValueError(f"unsupported seek mode: {whence}")
        if position < 0:
            raise ValueError("negative seek position")
        self._position = min(position, self._source.size)
        return self._position

    def readinto(self, buffer: bytearray | memoryview) -> int:
        self._checkClosed()
        remaining = self._source.size - self._position
        wanted = min(len(buffer), remaining)
        if wanted <= 0:
            return 0
        payload = self._source.read(self._position, wanted)
        buffer[:wanted] = payload
        self._position += wanted
        return wanted


@dataclass(frozen=True, slots=True)
class FileIdentity:
    device: int
    inode: int
    size: int
    mtime_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> FileIdentity:
        return cls(int(value.st_dev), int(value.st_ino), int(value.st_size), int(value.st_mtime_ns))


@dataclass(frozen=True, slots=True)
class SourceSlice:
    source: FileByteSource
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start

    def iter_chunks(self, *, chunk_size: int = 1 << 20) -> Iterator[bytes]:
        return self.source.iter_chunks(start=self.start, length=self.size, chunk_size=chunk_size)

    def materialize(self) -> bytes:
        self.source.budget.consume("materialized_bytes", self.size)
        return self.source.read(self.start, self.size)


class FileByteSource:
    def __init__(
        self,
        path: Path,
        *,
        limits: ResourceLimits | None = None,
        budget: BudgetTracker | None = None,
        allow_symlink: bool = False,
    ) -> None:
        supplied = Path(path)
        link_stat = os.lstat(supplied)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        is_reparse = stat.S_ISLNK(link_stat.st_mode) or bool(getattr(link_stat, "st_file_attributes", 0) & reparse_flag)
        if not allow_symlink and is_reparse:
            raise UnsafeSourceError(f"symbolic links are not accepted: {path}")
        self.path = supplied.resolve(strict=True)
        if not self.path.is_file():
            raise UnsafeSourceError(f"source is not a regular file: {path}")
        self.limits = limits or ResourceLimits()
        self.budget = budget or BudgetTracker(self.limits.budget_limits(), scope=f"source:{self.path.name}")
        self.identity = FileIdentity.from_stat(self.path.stat())
        if self.identity.size > self.limits.max_source_bytes:
            raise BudgetExceeded("source_bytes", self.limits.max_source_bytes, 0, self.identity.size)

    @property
    def size(self) -> int:
        return self.identity.size

    def _assert_unchanged(self, handle: BinaryIO | None = None) -> None:
        try:
            current = FileIdentity.from_stat(os.fstat(handle.fileno()) if handle is not None else self.path.stat())
        except OSError as exc:
            raise SourceChangedError(f"source is no longer accessible: {self.path}") from exc
        if current != self.identity:
            raise SourceChangedError(f"source identity changed while reading: {self.path}")

    def assert_unchanged(self) -> None:
        """Public identity checkpoint for parsers or tools using ``path``."""
        self._assert_unchanged()

    def open_reader(self, *, buffer_size: int = 1 << 20) -> io.BufferedReader:
        """Return a bounded, seekable parser view without materialization."""
        if buffer_size <= 0:
            raise ValueError("buffer_size must be greater than zero")
        self._assert_unchanged()
        return io.BufferedReader(SourceReader(self), buffer_size=buffer_size)

    def read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset > self.size or offset + length > self.size:
            raise ValueError("read range is outside the source")
        self.budget.consume("scanned_bytes", length)
        with self.path.open("rb", buffering=0) as handle:
            self._assert_unchanged(handle)
            handle.seek(offset)
            data = handle.read(length)
            if len(data) != length:
                raise SourceChangedError(f"short read from source: {self.path}")
            self._assert_unchanged(handle)
        self._assert_unchanged()
        return data

    def iter_chunks(
        self,
        *,
        start: int = 0,
        length: int | None = None,
        chunk_size: int = 1 << 20,
    ) -> Iterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        length = self.size - start if length is None else length
        if start < 0 or length < 0 or start > self.size or start + length > self.size:
            raise ValueError("stream range is outside the source")
        with self.path.open("rb", buffering=0) as handle:
            self._assert_unchanged(handle)
            handle.seek(start)
            remaining = length
            while remaining:
                wanted = min(chunk_size, remaining)
                self.budget.consume("scanned_bytes", wanted)
                chunk = handle.read(wanted)
                if len(chunk) != wanted:
                    raise SourceChangedError(f"short read from source: {self.path}")
                remaining -= len(chunk)
                yield chunk
            self._assert_unchanged(handle)
        self._assert_unchanged()

    def sha256(self, *, chunk_size: int = 1 << 20) -> str:
        digest = hashlib.sha256()
        for chunk in self.iter_chunks(chunk_size=chunk_size):
            digest.update(chunk)
        return digest.hexdigest()

    def slice(self, start: int = 0, end: int | None = None) -> SourceSlice:
        end = self.size if end is None else end
        if start < 0 or end < start or end > self.size:
            raise ValueError("slice range is outside the source")
        return SourceSlice(self, start, end)

    def prefix(self, length: int) -> bytes:
        return self.read(0, min(length, self.size))

    def tail(self, length: int) -> bytes:
        length = min(length, self.size)
        return self.read(self.size - length, length)
