from __future__ import annotations

import os
import threading
from dataclasses import asdict, dataclass
from typing import Callable, Mapping


class BudgetExceeded(RuntimeError):
    def __init__(self, name: str, limit: int | float, consumed: int | float, requested: int | float) -> None:
        self.name = name
        self.limit = limit
        self.consumed = consumed
        self.requested = requested
        self.attempted = consumed + requested
        super().__init__(f"{name} budget exceeded: attempted {self.attempted}, limit {limit}")


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    max_source_bytes: int = 4 * (1 << 30)
    # A source may be streamed once without being materialized. Keep the scan
    # ceiling aligned with the accepted source ceiling; materialization remains
    # separately constrained to 256 MiB by default.
    max_scanned_bytes: int = 4 * (1 << 30)
    max_candidates: int = 64
    max_candidate_bytes: int = 256 * (1 << 20)
    max_materialized_bytes: int = 256 * (1 << 20)
    max_decoder_seconds: float = 30.0
    max_tool_output_bytes: int = 1 << 20
    max_archive_members: int = 10_000
    max_archive_member_bytes: int = 256 * (1 << 20)
    max_decompressed_bytes: int = 1 << 30
    max_expansion_ratio: float = 100.0
    max_nesting_depth: int = 3
    max_artifacts: int = 1_000
    max_output_bytes: int = 2 * (1 << 30)
    max_workers: int = min(4, max(1, os.cpu_count() or 1))

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")

    def budget_limits(self) -> dict[str, int | float]:
        return {name.removeprefix("max_"): value for name, value in asdict(self).items()}


BudgetEventCallback = Callable[[dict[str, object]], None]


class BudgetTracker:
    """Thread-safe hierarchical counters with fail-before-consume semantics."""

    def __init__(
        self,
        limits: Mapping[str, int | float],
        *,
        scope: str = "run",
        on_event: BudgetEventCallback | None = None,
        _root: BudgetTracker | None = None,
    ) -> None:
        self.limits = dict(limits)
        if any(value <= 0 for value in self.limits.values()):
            raise ValueError("budget limits must be greater than zero")
        self.scope = scope
        self._on_event = on_event
        self._root = _root or self
        self._local: dict[str, int | float] = {}
        if _root is None:
            self._totals: dict[str, int | float] = {}
            self._lock = threading.RLock()

    def child(self, *, scope: str, limits: Mapping[str, int | float] | None = None) -> BudgetTracker:
        return BudgetTracker(limits or self.limits, scope=scope, on_event=self._on_event, _root=self._root)

    def consume(self, name: str, amount: int | float = 1) -> int | float:
        if amount < 0:
            raise ValueError("budget consumption cannot be negative")
        if amount == 0:
            return self.consumed(name)
        root = self._root
        with root._lock:
            limit = min(value for value in (root.limits.get(name), self.limits.get(name)) if value is not None)
            consumed = root._totals.get(name, 0)
            attempted = consumed + amount
            if attempted > limit:
                self._emit(name, limit, attempted, "exceeded")
                raise BudgetExceeded(name, limit, consumed, amount)
            root._totals[name] = attempted
            self._local[name] = self._local.get(name, 0) + amount
            self._emit(name, limit, attempted, "consumed")
            return attempted

    def check(self, name: str, amount: int | float) -> None:
        root = self._root
        with root._lock:
            limit = min(value for value in (root.limits.get(name), self.limits.get(name)) if value is not None)
            consumed = root._totals.get(name, 0)
            if consumed + amount > limit:
                self._emit(name, limit, consumed + amount, "exceeded")
                raise BudgetExceeded(name, limit, consumed, amount)

    def consumed(self, name: str) -> int | float:
        with self._root._lock:
            return self._root._totals.get(name, 0)

    def local_consumed(self, name: str) -> int | float:
        with self._root._lock:
            return self._local.get(name, 0)

    def remaining(self, name: str) -> int | float:
        limit = min(value for value in (self._root.limits.get(name), self.limits.get(name)) if value is not None)
        return max(0, limit - self.consumed(name))

    def snapshot(self) -> dict[str, int | float]:
        with self._root._lock:
            return dict(sorted(self._root._totals.items()))

    def _emit(self, name: str, limit: int | float, consumed: int | float, outcome: str) -> None:
        if self._on_event is not None:
            self._on_event(
                {"scope": self.scope, "name": name, "limit": limit, "consumed": consumed, "outcome": outcome}
            )
