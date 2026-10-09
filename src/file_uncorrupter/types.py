from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class RunState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    FAILED = "failed"


class FileStatus(str, Enum):
    DISCOVERED = "discovered"
    SCANNED = "scanned"
    CLASSIFIED = "classified"
    PROCESSING = "processing"
    RECOVERED = "recovered"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    BUDGET_EXCEEDED = "budget_exceeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OutcomeGrade(str, Enum):
    VALIDATED_ORIGINAL = "validated_original"
    VALIDATED_NORMALIZED = "validated_normalized"
    PARTIAL_CONTENT = "partial_content"
    PREVIEW_ONLY = "preview_only"
    UNAVAILABLE_DEPENDENCY = "unavailable_dependency"
    BUDGET_EXCEEDED = "budget_exceeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ArtifactKind(str, Enum):
    REPAIRED = "repaired"
    NORMALIZED = "normalized"
    EXTRACTED = "extracted"
    PREVIEW = "preview"
    FRAME = "frame"
    RAW_FRAGMENT = "raw_fragment"
    DIAGNOSTICS = "diagnostics"
    MANIFEST = "manifest"


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
    modified_ns: int = 0
    device_id: int = 0
    inode_id: int = 0


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
    strategy_hash: str = ""
    strategy_links: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        content_hash = hashlib.sha256(self.data).hexdigest()
        if not self.dedupe_hash:
            self.dedupe_hash = content_hash
        if not self.strategy_hash:
            strategy = {
                "strategy_id": self.strategy_id,
                "family": self.family,
                "priority": self.priority,
                "candidate_kind": self.candidate_kind,
                "provenance": self.provenance,
                "meta": self.meta,
                "data_sha256": content_hash,
            }
            self.strategy_hash = hashlib.sha256(json.dumps(strategy, sort_keys=True).encode("utf-8")).hexdigest()
        if not self.strategy_links:
            self.strategy_links.append(
                {
                    "strategy_hash": self.strategy_hash,
                    "strategy_id": self.strategy_id,
                    "priority": self.priority,
                    "provenance": self.provenance,
                    "meta": self.meta,
                }
            )

    @property
    def data_sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    def merge_strategy(self, other: Candidate) -> None:
        if self.dedupe_hash != other.dedupe_hash:
            raise ValueError("cannot merge candidates with different content identities")
        known = {str(link["strategy_hash"]) for link in self.strategy_links}
        for link in other.strategy_links:
            if str(link["strategy_hash"]) not in known:
                self.strategy_links.append(link)
                known.add(str(link["strategy_hash"]))
        self.strategy_links.sort(key=lambda link: (-int(link["priority"]), str(link["strategy_id"])))


@dataclass(frozen=True, slots=True)
class SourceSliceSpec:
    start: int
    end: int | None = None


@dataclass(frozen=True, slots=True)
class CandidatePlan:
    plan_id: str
    handler_id: str
    strategy_id: str
    family: str
    goal: str
    priority: int
    slices: tuple[SourceSliceSpec, ...] = ()
    prepend: bytes = b""
    append: bytes = b""
    estimated_materialized_bytes: int = 0
    estimated_output_bytes: int = 0
    provenance: tuple[dict[str, Any], ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)

    def materialize(self, source: Any, *, max_bytes: int) -> bytes:
        total = len(self.prepend) + len(self.append)
        for slice_spec in self.slices:
            end = source.size if slice_spec.end is None else slice_spec.end
            size = end - slice_spec.start
            if slice_spec.start < 0 or size < 0 or end > source.size:
                raise ValueError("candidate slice is outside the source")
            total += size
        if total > max_bytes:
            raise ValueError(f"candidate plan exceeds materialization limit {max_bytes}")

        budget = getattr(source, "budget", None)
        if budget is not None:
            budget.consume("materialized_bytes", total)

        parts: list[bytes] = [self.prepend]
        for slice_spec in self.slices:
            end = source.size if slice_spec.end is None else slice_spec.end
            size = end - slice_spec.start
            parts.extend(source.iter_chunks(start=slice_spec.start, length=size))
        parts.append(self.append)
        return b"".join(parts)


@dataclass(frozen=True, slots=True)
class ToolEvidence:
    name: str
    available: bool
    resolved_path: str | None = None
    version: str | None = None
    policy_id: str = "bounded-v1"
    exit_code: int | None = None
    timed_out: bool = False
    cancelled: bool = False
    duration_seconds: float = 0.0
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    cleanup_ok: bool = True


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
    size: int = 0
    media_type: str = "application/octet-stream"
    fidelity_grade: str = OutcomeGrade.PARTIAL_CONTENT.value
    validation_state: str = "unverified"
    validators: list[dict[str, Any]] = field(default_factory=list)
    published: bool = False
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
    grade: str = OutcomeGrade.FAILED.value
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
