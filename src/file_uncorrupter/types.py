from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SignatureHit:
    family: str
    signature_type: str
    offset: int
    confidence: float


@dataclass(slots=True)
class FileRecord:
    path: Path
    relative_path: Path
    size: int
    sha256: str
    declared_kind: str | None
    byte0_kind: str
    anywhere_kind: str
    signature_summary: dict[str, int] = field(default_factory=dict)
    signature_hits: list[SignatureHit] = field(default_factory=list)


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
    candidate_kind: str = "slice"
    provenance: list[dict[str, Any]] = field(default_factory=list)
    dedupe_hash: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dedupe_hash:
            payload = {
                "strategy_id": self.strategy_id,
                "family": self.family,
                "priority": self.priority,
                "candidate_kind": self.candidate_kind,
                "provenance": self.provenance,
                "meta": self.meta,
                "data_sha256": hashlib.sha256(self.data).hexdigest(),
            }
            self.dedupe_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    @property
    def data_sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(slots=True)
class Artifact:
    artifact_type: str
    path: Path
    sha256: str
    decoder: str
    width: int = 0
    height: int = 0
    duration_ms: int = 0
    frame_count: int = 0
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
    duration_ms: int = 0
    frame_count: int = 0
    telemetry: dict[str, Any] = field(default_factory=dict)

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(slots=True)
class RecoveryOutcome:
    candidate: Candidate | None
    decode: DecodeResult
    attempts: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
