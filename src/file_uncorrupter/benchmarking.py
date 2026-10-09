from __future__ import annotations

import ctypes
import hashlib
import json
import os
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any

from .paths import safe_relative_path
from .types import OutcomeGrade


_SUCCESS_GRADES = {
    OutcomeGrade.VALIDATED_ORIGINAL.value,
    OutcomeGrade.VALIDATED_NORMALIZED.value,
    OutcomeGrade.PARTIAL_CONTENT.value,
    OutcomeGrade.PREVIEW_ONLY.value,
}
_GRADE_RANK = {
    OutcomeGrade.VALIDATED_ORIGINAL.value: 4,
    OutcomeGrade.VALIDATED_NORMALIZED.value: 3,
    OutcomeGrade.PARTIAL_CONTENT.value: 2,
    OutcomeGrade.PREVIEW_ONLY.value: 1,
    OutcomeGrade.UNAVAILABLE_DEPENDENCY.value: 0,
    OutcomeGrade.BUDGET_EXCEEDED.value: 0,
    OutcomeGrade.CANCELLED.value: 0,
    OutcomeGrade.FAILED.value: 0,
}


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _windows_rss_bytes() -> int:
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    get_current_process = ctypes.windll.kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = wintypes.HANDLE
    get_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
    get_memory_info.restype = wintypes.BOOL
    process = get_current_process()
    if not get_memory_info(process, ctypes.byref(counters), counters.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return int(counters.WorkingSetSize)


def current_process_rss_bytes() -> tuple[int, str]:
    """Return current resident memory using only platform/stdlib facilities."""
    if os.name == "nt":
        return _windows_rss_bytes(), "windows_working_set"
    statm = Path("/proc/self/statm")
    if statm.is_file():
        fields = statm.read_text(encoding="ascii").split()
        if len(fields) >= 2:
            return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE")), "proc_statm_rss"
    try:
        import resource

        maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return (maximum if os.uname().sysname == "Darwin" else maximum * 1024), "resource_maxrss"
    except (AttributeError, ImportError, OSError, ValueError) as exc:
        raise RuntimeError("current process RSS is unavailable") from exc


class ProcessMemorySampler:
    """Sample main-process RSS during one benchmark recovery phase."""

    def __init__(self, *, interval_seconds: float = 0.02) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._baseline = 0
        self._peak = 0
        self._samples = 0
        self._method = "unavailable"
        self._error: str | None = None

    def _sample(self) -> None:
        try:
            value, method = current_process_rss_bytes()
            self._method = method
            self._peak = max(self._peak, value)
            self._samples += 1
        except Exception as exc:
            self._error = f"{exc.__class__.__name__}: {exc}"

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._sample()

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("memory sampler already started")
        self._sample()
        self._baseline = self._peak
        self._thread = threading.Thread(target=self._run, name="uncorrupter-memory-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        if self._thread is None:
            raise RuntimeError("memory sampler was not started")
        self._stop.set()
        self._thread.join(timeout=max(1.0, self.interval_seconds * 4))
        self._sample()
        return {
            "scope": "main_process_recovery_phase",
            "children_included": False,
            "method": self._method,
            "sample_interval_seconds": self.interval_seconds,
            "sample_count": self._samples,
            "baseline_memory_bytes": self._baseline or None,
            "peak_memory_bytes": self._peak or None,
            "peak_over_baseline_bytes": max(0, self._peak - self._baseline) if self._peak and self._baseline else None,
            "error": self._error,
        }


def load_ground_truth(path: Path) -> dict[str, Any]:
    resolved = Path(path).resolve(strict=True)
    if resolved.stat().st_size > 16 * (1 << 20):
        raise ValueError("ground-truth JSON exceeds the 16 MiB metadata limit")
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"ground-truth JSON is invalid: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1 or not isinstance(raw.get("files"), dict):
        raise ValueError("ground truth must be an object with schema_version=1 and a files object")
    if len(raw["files"]) > 100_000:
        raise ValueError("ground truth exceeds the 100000-file evaluation limit")

    entries: dict[str, dict[str, Any]] = {}
    known_grades = {grade.value for grade in OutcomeGrade}
    for supplied_path, supplied in raw["files"].items():
        if not isinstance(supplied_path, str) or not isinstance(supplied, dict):
            raise ValueError("ground-truth file entries must map relative path strings to objects")
        relative = safe_relative_path(supplied_path).as_posix()
        key = relative.casefold()
        if key in entries:
            raise ValueError(f"duplicate ground-truth path after normalization: {relative}")
        family = supplied.get("family")
        recoverable = supplied.get("recoverable")
        acceptable = supplied.get("acceptable_grades", [])
        source_sha256 = supplied.get("source_sha256")
        if family is not None and (not isinstance(family, str) or not family.strip()):
            raise ValueError(f"{relative}: family must be a non-empty string or null")
        if recoverable is not None and not isinstance(recoverable, bool):
            raise ValueError(f"{relative}: recoverable must be boolean or null")
        if not isinstance(acceptable, list) or any(item not in known_grades for item in acceptable):
            raise ValueError(f"{relative}: acceptable_grades contains an unknown outcome grade")
        if source_sha256 is not None and (
            not isinstance(source_sha256, str)
            or len(source_sha256) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in source_sha256)
        ):
            raise ValueError(f"{relative}: source_sha256 must be a 64-character hexadecimal digest")
        if family is None and recoverable is None and not acceptable:
            raise ValueError(f"{relative}: at least one expectation is required")
        entries[key] = {
            "relative_path": relative,
            "family": family.strip() if isinstance(family, str) else None,
            "recoverable": recoverable,
            "acceptable_grades": sorted(set(acceptable)),
            "source_sha256": source_sha256.lower() if isinstance(source_sha256, str) else None,
        }
    return {
        "schema_version": 1,
        "dataset_name": str(raw.get("dataset_name") or resolved.stem)[:200],
        "source_name": resolved.name,
        "source_sha256": _sha256_path(resolved),
        "entries": entries,
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 12) if denominator else None


def evaluate_ground_truth(conn, run_id: int, dataset: dict[str, Any]) -> dict[str, Any]:
    file_rows = conn.execute(
        """
        SELECT relative_path, sha256, classification_family, classification_label, status
        FROM files WHERE run_id = ? ORDER BY relative_path COLLATE NOCASE, id
        """,
        (run_id,),
    ).fetchall()
    observed: dict[str, dict[str, Any]] = {}
    for row in file_rows:
        relative = str(row["relative_path"])
        observed[relative.replace("\\", "/").casefold()] = {
            "relative_path": relative.replace("\\", "/"),
            "source_sha256": str(row["sha256"]),
            "family": row["classification_family"],
            "label": row["classification_label"],
            "status": str(row["status"]),
            "grades": [],
            "successful_outputs": 0,
        }

    for row in conn.execute(
        """
        SELECT f.relative_path, a.outcome_grade
        FROM attempts a JOIN files f ON f.id = a.file_id
        WHERE a.run_id = ? AND a.outcome_grade IS NOT NULL
        ORDER BY f.relative_path COLLATE NOCASE, a.id
        """,
        (run_id,),
    ).fetchall():
        key = str(row["relative_path"]).replace("\\", "/").casefold()
        if key in observed:
            grade = str(row["outcome_grade"])
            if grade not in observed[key]["grades"]:
                observed[key]["grades"].append(grade)
    for row in conn.execute(
        """
        SELECT f.relative_path, COUNT(o.id) AS successful_outputs
        FROM files f LEFT JOIN outputs o ON o.file_id = f.id AND o.run_id = f.run_id AND o.success = 1
        WHERE f.run_id = ? GROUP BY f.id, f.relative_path
        """,
        (run_id,),
    ).fetchall():
        key = str(row["relative_path"]).replace("\\", "/").casefold()
        if key in observed:
            observed[key]["successful_outputs"] = int(row["successful_outputs"])

    totals: defaultdict[str, int] = defaultdict(int)
    groups: dict[str, defaultdict[str, int]] = {}
    results: list[dict[str, Any]] = []
    expected_keys = set(dataset["entries"])
    for key, expected in sorted(dataset["entries"].items(), key=lambda item: item[1]["relative_path"].casefold()):
        actual = observed.get(key)
        group_name = str(expected["family"] or "unlabeled")
        group = groups.setdefault(group_name, defaultdict(int))
        totals["expected_files"] += 1
        group["expected_files"] += 1
        if actual is None:
            totals["missing_files"] += 1
            group["missing_files"] += 1
            results.append({"relative_path": expected["relative_path"], "state": "missing", "expected": expected})
            continue

        identity_match = expected["source_sha256"] is None or expected["source_sha256"] == actual["source_sha256"]
        if not identity_match:
            totals["identity_mismatches"] += 1
            group["identity_mismatches"] += 1
        family_match: bool | None = None
        if expected["family"] is not None:
            totals["classification_labeled"] += 1
            group["classification_labeled"] += 1
            family_match = expected["family"] in {actual["family"], actual["label"]}
            if family_match and identity_match:
                totals["classification_correct"] += 1
                group["classification_correct"] += 1

        grades = sorted(actual["grades"], key=lambda grade: (-_GRADE_RANK.get(grade, -1), grade))
        recovery_claim = (
            actual["successful_outputs"] > 0
            or actual["status"] in {"recovered", "partial"}
            or any(grade in _SUCCESS_GRADES for grade in grades)
        )
        recovery_match: bool | None = None
        if expected["recoverable"] is not None:
            totals["recoverability_labeled"] += 1
            group["recoverability_labeled"] += 1
            if expected["recoverable"]:
                totals["positive_samples"] += 1
                group["positive_samples"] += 1
                recovery_match = recovery_claim
                if not recovery_claim and identity_match:
                    totals["false_negatives"] += 1
                    group["false_negatives"] += 1
            else:
                totals["negative_samples"] += 1
                group["negative_samples"] += 1
                recovery_match = not recovery_claim
                if recovery_claim and identity_match:
                    totals["false_positives"] += 1
                    group["false_positives"] += 1
            if recovery_match and identity_match:
                totals["recovery_correct"] += 1
                group["recovery_correct"] += 1

        fidelity_match: bool | None = None
        if expected["acceptable_grades"]:
            totals["fidelity_labeled"] += 1
            group["fidelity_labeled"] += 1
            fidelity_match = any(grade in expected["acceptable_grades"] for grade in grades)
            if fidelity_match and identity_match:
                totals["fidelity_correct"] += 1
                group["fidelity_correct"] += 1
        results.append(
            {
                "relative_path": expected["relative_path"],
                "state": "evaluated" if identity_match else "identity_mismatch",
                "expected": expected,
                "observed": actual,
                "classification_match": family_match,
                "recovery_match": recovery_match,
                "fidelity_match": fidelity_match,
            }
        )

    extra_files = sorted(actual["relative_path"] for key, actual in observed.items() if key not in expected_keys)

    def group_metrics(values: defaultdict[str, int]) -> dict[str, Any]:
        payload = dict(sorted(values.items()))
        payload.update(
            {
                "classification_accuracy": _rate(values["classification_correct"], values["classification_labeled"]),
                "recovery_accuracy": _rate(values["recovery_correct"], values["recoverability_labeled"]),
                "false_positive_rate": _rate(values["false_positives"], values["negative_samples"]),
                "false_negative_rate": _rate(values["false_negatives"], values["positive_samples"]),
                "fidelity_accuracy": _rate(values["fidelity_correct"], values["fidelity_labeled"]),
            }
        )
        return payload

    return {
        "schema_version": dataset["schema_version"],
        "dataset_name": dataset["dataset_name"],
        "source_name": dataset["source_name"],
        "source_sha256": dataset["source_sha256"],
        "metrics": group_metrics(totals),
        "groups": {name: group_metrics(values) for name, values in sorted(groups.items())},
        "extra_files": extra_files,
        "files": results,
    }
