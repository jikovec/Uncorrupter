from __future__ import annotations

import csv
import copy
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .atomic import AtomicArtifactWriter, CollisionPolicy
from .db import fetch_attempt_rows, fetch_manifest_rows, fetch_run, fetch_summary
from .events import redact_paths


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _redact(value: Any, roots: Iterable[Path] | None, salt: str) -> Any:
    selected = [Path(root) for root in (roots or [])]
    return redact_paths(_json_value(value), roots=selected, salt=salt) if selected else _json_value(value)


def _publish(path: Path, payload: bytes, collision_policy: CollisionPolicy | str) -> Path:
    return AtomicArtifactWriter(path.parent, collision_policy=collision_policy).publish_bytes(path.name, payload).path


def benchmark_metrics(conn, run_id: int) -> dict[str, Any]:
    summary = fetch_summary(conn, run_id)
    run = fetch_run(conn, run_id)
    input_bytes = int(conn.execute("SELECT COALESCE(SUM(size), 0) FROM files WHERE run_id = ?", (run_id,)).fetchone()[0])
    output_bytes = int(conn.execute("SELECT COALESCE(SUM(size), 0) FROM outputs WHERE run_id = ? AND success = 1", (run_id,)).fetchone()[0])
    timeout_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM tool_records WHERE run_id = ? AND evidence_json LIKE '%\"timed_out\": true%'",
            (run_id,),
        ).fetchone()[0]
    )
    total = int(summary["total_files"])
    recovered = int(summary["recovered"])
    partial = int(summary["partial"])
    duration_seconds = None
    if run["started_at"] and run["finished_at"]:
        try:
            duration_seconds = max(
                0.0,
                (datetime.fromisoformat(str(run["finished_at"]).replace("Z", "+00:00")) - datetime.fromisoformat(str(run["started_at"]).replace("Z", "+00:00"))).total_seconds(),
            )
        except ValueError:
            duration_seconds = None
    observation_row = conn.execute(
        """
        SELECT payload_json FROM events
        WHERE run_id = ? AND event_type = 'benchmark.observed'
        ORDER BY sequence DESC LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    observation: dict[str, Any] = {}
    if observation_row is not None:
        try:
            loaded = json.loads(observation_row["payload_json"])
            observation = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            observation = {"error": "persisted benchmark observation is invalid JSON"}
    ground_truth = observation.get("ground_truth") if isinstance(observation.get("ground_truth"), dict) else None
    ground_truth_metrics = ground_truth.get("metrics", {}) if ground_truth else {}
    memory = observation.get("memory") if isinstance(observation.get("memory"), dict) else {}
    return {
        "recovery": {
            "total_files": total,
            "recovered": recovered,
            "partial": partial,
            "success_rate": recovered / total if total else 0.0,
            "partial_success_rate": (recovered + partial) / total if total else 0.0,
            "false_positive_rate": ground_truth_metrics.get("false_positive_rate"),
            "false_negative_rate": ground_truth_metrics.get("false_negative_rate"),
            "classification_accuracy": ground_truth_metrics.get("classification_accuracy"),
            "ground_truth_recovery_accuracy": ground_truth_metrics.get("recovery_accuracy"),
            "false_positive_note": (
                f"measured against {ground_truth.get('dataset_name')}"
                if ground_truth
                else "ground-truth labels were not supplied"
            ),
        },
        "fidelity": summary["by_outcome_grade"],
        "ground_truth": ground_truth,
        "performance": {
            "duration_seconds": duration_seconds,
            "peak_memory_bytes": memory.get("peak_memory_bytes"),
            "peak_over_baseline_bytes": memory.get("peak_over_baseline_bytes"),
            "baseline_memory_bytes": memory.get("baseline_memory_bytes"),
            "memory_measurement": memory or None,
            "peak_memory_note": (
                "sampled main-process RSS during the recovery phase; child tool processes are excluded"
                if memory.get("peak_memory_bytes") is not None
                else "not measured; run the benchmark command to capture process RSS"
            ),
            "input_bytes": input_bytes,
            "output_bytes": output_bytes,
            "output_expansion_ratio": output_bytes / input_bytes if input_bytes else 0.0,
        },
        "reliability": {
            "crashes": int(summary["by_status"].get("failed", 0)),
            "timeouts": timeout_count,
            "budget_stops": summary["budget_stops"],
            "cancelled": int(summary["by_status"].get("cancelled", 0)),
        },
    }


def build_final_manifest(
    conn,
    run_id: int,
    *,
    redact_roots: Iterable[Path] | None = None,
    redaction_salt: str = "uncorrupter",
    include_benchmark: bool = True,
) -> dict[str, Any]:
    run = fetch_run(conn, run_id)
    summary = fetch_summary(conn, run_id)
    files: dict[int, dict[str, Any]] = {}
    for row in fetch_manifest_rows(conn, run_id):
        file_id = int(row["file_id"])
        item = files.setdefault(
            file_id,
            {
                "relative_path": row["relative_path"],
                "size": int(row["size"]),
                "source_sha256": row["source_sha256"],
                "classification": {
                    "family": row["classification_family"],
                    "label": row["classification_label"],
                    "confidence": row["classification_confidence"],
                },
                "status": row["status"],
                "error_code": row["error_code"],
                "error_detail": row["error_detail"],
                "artifacts": [],
            },
        )
        if row["output_id"] is not None:
            item["artifacts"].append(
                {
                    "type": row["output_type"],
                    "path": row["output_path"],
                    "sha256": row["artifact_sha256"],
                    "media_type": row["media_type"],
                    "size": row["output_size"],
                    "fidelity_grade": row["fidelity_grade"] or row["outcome_grade"],
                    "validation_state": row["validation_state"],
                    "publication_state": row["publication_state"],
                    "success": bool(row["success"]),
                    "error": row["error"],
                    "decoder": row["decoder"],
                    "phase": row["phase"],
                }
            )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "application": "file-uncorrupter",
        "run": {
            "id": run_id,
            "command": run["command"],
            "state": run["state"],
            "input_root": run["input_root"],
            "output_root": run["output_root"],
            "workspace_root": run["workspace_root"],
            "database_path": run["database_path"],
            "engine_name": run["engine_name"],
            "application_version": run["application_version"],
            "goals": json.loads(run["goals_json"] or "[]"),
            "config": json.loads(run["config_json"] or "{}"),
            "platform": json.loads(run["platform_json"] or "{}"),
            "tools": json.loads(run["tools_json"] or "{}"),
            "resume_of_run_id": run["resume_of_run_id"],
            "created_at": run["created_at"],
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "cancellation_reason": run["cancellation_reason"],
            "fatal_error": run["fatal_error"],
        },
        "summary": summary,
        "files": list(files.values()),
    }
    if include_benchmark:
        manifest["benchmark"] = benchmark_metrics(conn, run_id)
    return _redact(manifest, redact_roots, redaction_salt)


def normalized_manifest_for_comparison(manifest: dict[str, Any]) -> dict[str, Any]:
    """Remove run-local coordinates and measurements for reproducibility checks."""
    normalized = copy.deepcopy(manifest)
    run = normalized.get("run") if isinstance(normalized.get("run"), dict) else {}
    output_root = Path(str(run.get("output_root"))).resolve() if run.get("output_root") else None
    for key in (
        "id",
        "input_root",
        "output_root",
        "workspace_root",
        "database_path",
        "created_at",
        "started_at",
        "finished_at",
        "resume_of_run_id",
    ):
        if key in run:
            run[key] = None

    files = normalized.get("files") if isinstance(normalized.get("files"), list) else []
    for item in files:
        if not isinstance(item, dict):
            continue
        artifacts = item.get("artifacts") if isinstance(item.get("artifacts"), list) else []
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not artifact.get("path"):
                continue
            path = Path(str(artifact["path"]))
            if output_root is not None:
                try:
                    artifact["path"] = path.resolve().relative_to(output_root).as_posix()
                except ValueError:
                    artifact["path"] = path.name
            else:
                artifact["path"] = path.name
        artifacts.sort(key=lambda value: (str(value.get("path")), str(value.get("type")), str(value.get("sha256"))))
    files.sort(key=lambda value: str(value.get("relative_path", "")).casefold())

    summary = normalized.get("summary") if isinstance(normalized.get("summary"), dict) else {}
    for key in ("run_id", "input_root", "output_root", "workspace_root", "created_at", "started_at", "finished_at", "resume_of_run_id"):
        if key in summary:
            summary[key] = None
    benchmark = normalized.get("benchmark") if isinstance(normalized.get("benchmark"), dict) else {}
    performance = benchmark.get("performance") if isinstance(benchmark.get("performance"), dict) else {}
    for key in (
        "duration_seconds",
        "peak_memory_bytes",
        "peak_over_baseline_bytes",
        "baseline_memory_bytes",
        "memory_measurement",
        "peak_memory_note",
    ):
        if key in performance:
            performance[key] = None
    return normalized


def write_json_report(
    conn,
    run_id: int,
    output_path: Path,
    *,
    redact_roots: Iterable[Path] | None = None,
    redaction_salt: str = "uncorrupter",
    collision_policy: CollisionPolicy | str = CollisionPolicy.FAIL,
) -> dict[str, Any]:
    report = build_final_manifest(
        conn,
        run_id,
        redact_roots=redact_roots,
        redaction_salt=redaction_salt,
    )
    payload = (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    _publish(Path(output_path), payload, collision_policy)
    return report


def write_attempts_csv(
    conn,
    run_id: int,
    output_path: Path,
    *,
    redact_roots: Iterable[Path] | None = None,
    redaction_salt: str = "uncorrupter",
    collision_policy: CollisionPolicy | str = CollisionPolicy.FAIL,
) -> Path:
    rows = fetch_attempt_rows(conn, run_id)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "relative_path", "file_status", "outcome_grade", "strategy_id", "family", "priority",
        "phase", "decoder", "ok", "width", "height", "mode", "decoded_format",
        "duration_ms", "frame_count", "score", "error",
    ])
    for row in rows:
        values = [
            row["relative_path"], row["file_status"], row["outcome_grade"], row["strategy_id"],
            row["family"], row["priority"], row["phase"], row["decoder"], row["ok"],
            row["width"], row["height"], row["mode"], row["decoded_format"], row["duration_ms"],
            row["frame_count"], row["score"], row["error"],
        ]
        writer.writerow(_redact(values, redact_roots, redaction_salt))
    return _publish(Path(output_path), buffer.getvalue().encode("utf-8"), collision_policy)


def write_text_report(
    conn,
    run_id: int,
    output_path: Path,
    *,
    redact_roots: Iterable[Path] | None = None,
    redaction_salt: str = "uncorrupter",
    collision_policy: CollisionPolicy | str = CollisionPolicy.FAIL,
) -> Path:
    summary = _redact(fetch_summary(conn, run_id), redact_roots, redaction_salt)
    lines = [
        f"Uncorrupter run {summary['run_id']}",
        f"state: {summary['state']}",
        f"files: {summary['total_files']}",
        f"recovered: {summary['recovered']}",
        f"partial: {summary['partial']}",
        f"failed: {summary['failed']}",
        "statuses:",
    ]
    lines.extend(f"  {key}: {value}" for key, value in sorted(summary["by_status"].items()))
    lines.append("outcome grades:")
    lines.extend(f"  {key}: {value}" for key, value in sorted(summary["by_outcome_grade"].items()))
    return _publish(Path(output_path), ("\n".join(lines) + "\n").encode("utf-8"), collision_policy)
