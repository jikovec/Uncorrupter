from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from ..budgets import BudgetTracker, ResourceLimits
from ..byte_source import FileByteSource
from ..cancellation import CancellationToken
from ..types import CandidatePlan, Classification, FileRecord, RecoveryOutcome


class OperationLevel(str, Enum):
    NONE = "none"
    DETECT = "detect"
    INSPECT = "inspect"
    BASELINE = "baseline"
    PARTIAL = "partial"
    VALIDATED = "validated"


class RecoveryGoal(str, Enum):
    REPAIR = "repair"
    NORMALIZE = "normalize"
    EXTRACT = "extract"
    PREVIEW = "preview"
    CARVE = "carve"


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    family: str
    variants: tuple[str, ...]
    extensions: tuple[str, ...]
    signatures: tuple[str, ...]
    operations: dict[str, str]
    tools: dict[str, tuple[str, ...]]
    limits: dict[str, int | float]
    encryption: str
    active_content: str
    outputs: tuple[dict[str, str], ...]
    fidelity: str
    fixtures: tuple[str, ...]
    availability: str = "available"
    unavailable_reasons: tuple[str, ...] = ()
    handler_id: str = ""

    def __post_init__(self) -> None:
        expected = {"detect", "inspect", "validate", "repair", "normalize", "extract", "preview", "carve"}
        if set(self.operations) != expected:
            raise ValueError(f"capability operations must be exactly {sorted(expected)}")
        valid_levels = {item.value for item in OperationLevel}
        invalid = set(self.operations.values()) - valid_levels
        if invalid:
            raise ValueError(f"invalid operation levels: {sorted(invalid)}")
        if self.availability not in {"available", "partial", "unavailable"}:
            raise ValueError(f"invalid availability: {self.availability}")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["variants"] = list(self.variants)
        value["extensions"] = list(self.extensions)
        value["signatures"] = list(self.signatures)
        value["tools"] = {key: list(items) for key, items in self.tools.items()}
        value["outputs"] = list(self.outputs)
        value["fixtures"] = list(self.fixtures)
        value["unavailable_reasons"] = list(self.unavailable_reasons)
        return value


@dataclass(slots=True)
class InspectionResult:
    family: str
    valid: bool
    confidence: float
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    parts: list[dict[str, Any]] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HandlerContext:
    source: FileByteSource
    record: FileRecord
    classification: Classification
    limits: ResourceLimits
    budget: BudgetTracker
    cancellation: CancellationToken
    output_root: Path | None = None


class FormatHandler(ABC):
    handler_id: str

    @abstractmethod
    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def inspect(self, context: HandlerContext) -> InspectionResult:
        raise NotImplementedError

    @abstractmethod
    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        raise NotImplementedError
