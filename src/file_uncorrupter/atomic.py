from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

from .budgets import BudgetTracker
from .paths import contained_path


class CollisionError(FileExistsError):
    pass


class ValidationError(RuntimeError):
    pass


class CollisionPolicy(str, Enum):
    FAIL = "fail"
    SUFFIX = "suffix"
    REPLACE = "replace"


@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    path: Path
    sha256: str
    size: int
    atomic: bool
    collision_policy: str


Validator = Callable[[Path], bool | None]


class AtomicArtifactWriter:
    def __init__(
        self,
        root: Path,
        *,
        collision_policy: CollisionPolicy | str = CollisionPolicy.FAIL,
        budget: BudgetTracker | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.collision_policy = CollisionPolicy(collision_policy)
        self.budget = budget

    def publish_bytes(self, relative: str | os.PathLike[str], data: bytes, *, validator: Validator | None = None) -> PublishedArtifact:
        return self.publish_stream(relative, (data,), validator=validator)

    def publish_stream(
        self,
        relative: str | os.PathLike[str],
        chunks: Iterable[bytes],
        *,
        validator: Validator | None = None,
    ) -> PublishedArtifact:
        if self.budget is not None:
            self.budget.consume("artifacts", 1)
        destination = contained_path(self.root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.parent / f".{destination.name}.uncorrupter-{uuid.uuid4().hex}.tmp"
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("xb") as handle:
                for chunk in chunks:
                    if not isinstance(chunk, bytes):
                        raise TypeError("artifact chunks must be bytes")
                    if self.budget is not None:
                        self.budget.consume("output_bytes", len(chunk))
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if validator is not None:
                try:
                    accepted = validator(temporary)
                except Exception as exc:
                    raise ValidationError(f"artifact validation raised: {exc}") from exc
                if accepted is False:
                    raise ValidationError("artifact validation rejected the temporary output")
            published, atomic = self._publish(temporary, destination)
            self._flush_directory(published.parent)
            return PublishedArtifact(published, digest.hexdigest(), size, atomic, self.collision_policy.value)
        finally:
            temporary.unlink(missing_ok=True)

    def _publish(self, temporary: Path, destination: Path) -> tuple[Path, bool]:
        if self.collision_policy is CollisionPolicy.REPLACE:
            os.replace(temporary, destination)
            return destination, True
        if self.collision_policy is CollisionPolicy.FAIL:
            return self._publish_exclusive(temporary, destination)
        counter = 1
        while True:
            candidate = destination.with_name(f"{destination.stem} ({counter}){destination.suffix}")
            try:
                return self._publish_exclusive(temporary, candidate)
            except CollisionError:
                counter += 1

    @staticmethod
    def _publish_exclusive(temporary: Path, destination: Path) -> tuple[Path, bool]:
        try:
            os.link(temporary, destination)
            temporary.unlink()
            return destination, True
        except FileExistsError as exc:
            raise CollisionError(f"destination already exists: {destination}") from exc
        except OSError:
            try:
                with destination.open("xb") as target, temporary.open("rb") as source:
                    shutil.copyfileobj(source, target, length=1 << 20)
                    target.flush()
                    os.fsync(target.fileno())
                temporary.unlink()
                return destination, False
            except FileExistsError as exc:
                raise CollisionError(f"destination already exists: {destination}") from exc
            except Exception:
                destination.unlink(missing_ok=True)
                raise

    @staticmethod
    def _flush_directory(directory: Path) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
