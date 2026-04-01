from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FileRecord:
    path: Path
    relative_path: Path
    size: int
    sha256: str
    declared_kind: str | None
    byte0_kind: str


@dataclass(slots=True)
class Classification:
    family: str
    label: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Candidate:
    strategy_id: str
    family: str
    priority: int
    data: bytes
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DecodeResult:
    ok: bool
    decoder: str
    width: int = 0
    height: int = 0
    mode: str = ""
    decoded_format: str = ""
    error: str = ""
    score: float = 0.0
    output_path: Path | None = None

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(slots=True)
class RecoveryOutcome:
    candidate: Candidate | None
    decode: DecodeResult
    attempts: list[dict[str, Any]] = field(default_factory=list)
