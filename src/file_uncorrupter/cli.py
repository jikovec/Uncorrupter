from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import stat
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .atomic import CollisionError, CollisionPolicy
from .benchmarking import ProcessMemorySampler, evaluate_ground_truth, load_ground_truth
from .budgets import ResourceLimits
from .cancellation import CancellationToken
from .capabilities import build_capability_manifest, capability_json, capability_markdown, capability_text, write_capability_manifest
from .db import (
    connect,
    fetch_resume_files,
    fetch_run,
    fetch_summary,
    file_transaction,
    insert_event,
    latest_run_id,
    source_identity_matches,
    start_run,
    transition_file,
    transition_run,
)
from .events import MachineEventWriter
from .handlers.base import RecoveryGoal
from .paths import PathLayoutError, validate_layout
from .pipeline import FileAnalysis, FileExecution, RecoveryPipeline
from .process_runner import ProcessPolicy, configure_process_isolation, probe_tool
from .reporting import write_attempts_csv, write_json_report, write_text_report
from .workspace import WorkspaceLayout, build_workspace_layout


EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FATAL = 2
EXIT_NO_RESULTS = 3


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _add_limits(target: argparse.ArgumentParser) -> None:
    defaults = ResourceLimits()
    integer_options = (
        "max_source_bytes", "max_scanned_bytes", "max_candidates", "max_candidate_bytes",
        "max_materialized_bytes", "max_tool_output_bytes", "max_archive_members",
        "max_archive_member_bytes", "max_decompressed_bytes", "max_nesting_depth",
        "max_artifacts", "max_output_bytes", "max_workers",
    )
    for name in integer_options:
        option = "--workers" if name == "max_workers" else "--" + name.replace("_", "-")
        aliases = [option]
        if name == "max_workers":
            aliases.append("--max-workers")
        target.add_argument(*aliases, dest=name, type=_positive_int, default=getattr(defaults, name))
    target.add_argument("--max-decoder-seconds", type=_positive_float, default=defaults.max_decoder_seconds)
    target.add_argument("--max-expansion-ratio", type=_positive_float, default=defaults.max_expansion_ratio)


def _add_common_scan_args(target: argparse.ArgumentParser) -> None:
    target.add_argument("input_root", type=Path)
    target.add_argument("--recursive", action="store_true")
    target.add_argument("--all-files", action="store_true")
    target.add_argument("--db", type=Path, default=Path("runs.sqlite3"))
    target.add_argument("--workspace-root", type=Path)
    target.add_argument("--engine", default="baseline-v2")
    target.add_argument("--complete-limit", type=_positive_int)
    target.add_argument("--cancel-marker", type=Path)
    target.add_argument("--events", type=Path)
    target.add_argument("--allow-risky-layout", action="store_true")
    target.add_argument("--redact-paths", action="store_true")
    target.add_argument("--redaction-salt", default="uncorrupter")
    target.add_argument("--quiet", action="store_true")
    _add_limits(target)


def _add_recovery_args(target: argparse.ArgumentParser) -> None:
    target.add_argument("output_root", type=Path)
    target.add_argument(
        "--goal",
        dest="goals",
        action="append",
        choices=[goal.value for goal in RecoveryGoal],
        help="Repeat to request multiple distinct operations; defaults to repair.",
    )
    target.add_argument("--save-raw-candidates", action="store_true")
    target.add_argument("--resume", type=_positive_int, metavar="RUN_ID")
    target.add_argument("--changed-input-policy", choices=("abort", "reprocess", "skip"), default="abort")
    target.add_argument("--exit-policy", choices=("strict", "partial-ok", "report-only"), default="strict")
    target.add_argument("--manifest", type=Path)
    target.add_argument("--output-json", type=Path, help=argparse.SUPPRESS)
    target.add_argument("--output-csv", type=Path)
    target.add_argument("--output-text", type=Path)
    target.add_argument("--require-tool-isolation", action="store_true")
    target.add_argument("--isolation-wrapper", nargs="+", metavar="ARG")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-uncorrupter",
        description="Bounded, evidence-preserving recovery for untrusted files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capabilities = subparsers.add_parser("capabilities", help="Print executable format capabilities.")
    capabilities.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    capabilities.add_argument("--output", type=Path)

    scan = subparsers.add_parser("scan", help="Inventory and detect signatures without classification or recovery.")
    _add_common_scan_args(scan)

    classify = subparsers.add_parser("classify", help="Inventory, detect, and classify without recovery.")
    _add_common_scan_args(classify)

    recover = subparsers.add_parser("recover", help="Execute only explicitly requested recovery goals.")
    _add_common_scan_args(recover)
    _add_recovery_args(recover)

    benchmark = subparsers.add_parser("benchmark", help="Recover and emit benchmark metrics in the final manifest.")
    _add_common_scan_args(benchmark)
    _add_recovery_args(benchmark)
    benchmark.add_argument(
        "--ground-truth",
        type=Path,
        help="JSON v1 expectations outside input_root for false-positive, classification, recovery, and fidelity metrics.",
    )

    report = subparsers.add_parser("report", help="Render durable reports for a persisted run.")
    report.add_argument("--db", type=Path, default=Path("runs.sqlite3"))
    report.add_argument("--run-id", type=_positive_int)
    report.add_argument("--output-json", type=Path)
    report.add_argument("--output-csv", type=Path)
    report.add_argument("--output-text", type=Path)
    report.add_argument("--redact-paths", action="store_true")
    report.add_argument("--redaction-salt", default="uncorrupter")

    return parser


def _limits_from_args(args: argparse.Namespace) -> ResourceLimits:
    return ResourceLimits(**{item.name: getattr(args, item.name) for item in fields(ResourceLimits)})


def _goals(args: argparse.Namespace) -> tuple[RecoveryGoal, ...]:
    values = args.goals or [RecoveryGoal.REPAIR.value]
    ordered: list[RecoveryGoal] = []
    for value in values:
        goal = RecoveryGoal(value)
        if goal not in ordered:
            ordered.append(goal)
    return tuple(ordered)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _prepare_layout(args: argparse.Namespace, output_root: Path | None) -> tuple[Path, Path | None, WorkspaceLayout]:
    supplied_input = Path(args.input_root)
    input_stat = os.lstat(supplied_input)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(input_stat.st_mode) or bool(getattr(input_stat, "st_file_attributes", 0) & reparse_flag):
        raise PathLayoutError("symbolic-link or reparse input roots are not accepted")
    input_root = supplied_input.resolve(strict=True)
    resolved_output = Path(output_root).resolve() if output_root is not None else None
    layout = build_workspace_layout(
        input_root=input_root,
        db_path=Path(args.db),
        output_root=resolved_output,
        workspace_root=args.workspace_root,
    )
    validation = validate_layout(
        input_root,
        resolved_output or layout.outputs_dir,
        layout.root,
        layout.db_path,
        allow_risky=bool(args.allow_risky_layout),
    )
    layout.root = validation["workspace_root"]
    layout.db_path = validation["database_path"]
    layout.blobs_dir = layout.root / "blobs"
    layout.outputs_dir = layout.root / "outputs"
    layout.reports_dir = layout.root / "reports"
    layout.configs_dir = layout.root / "configs"
    if resolved_output is not None:
        resolved_output = validation["output_root"]
    for optional_path in (getattr(args, "events", None), getattr(args, "manifest", None), getattr(args, "output_csv", None), getattr(args, "output_text", None)):
        if optional_path is not None and _is_within(Path(optional_path), input_root) and not args.allow_risky_layout:
            raise PathLayoutError(f"report or event path overlaps input_root: {optional_path}")
    return input_root, resolved_output, layout


def _effective_config(
    args: argparse.Namespace,
    limits: ResourceLimits,
    goals: Iterable[RecoveryGoal] = (),
    *,
    ground_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "recursive": bool(args.recursive),
        "all_files": bool(args.all_files),
        "engine": args.engine,
        "goals": [goal.value for goal in goals],
        "limits": asdict(limits),
        "complete_limit": args.complete_limit,
        "save_raw_candidates": bool(getattr(args, "save_raw_candidates", False)),
        "required_tool_isolation": bool(getattr(args, "require_tool_isolation", False)),
        "isolation_wrapper": list(getattr(args, "isolation_wrapper", None) or []),
        "benchmark_ground_truth": (
            {
                "dataset_name": ground_truth["dataset_name"],
                "source_name": ground_truth["source_name"],
                "source_sha256": ground_truth["source_sha256"],
                "entry_count": len(ground_truth["entries"]),
            }
            if ground_truth is not None
            else None
        ),
    }


def _platform_evidence() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def _tool_evidence(capability_manifest: dict[str, Any]) -> dict[str, Any]:
    names = sorted(
        {
            name
            for capability in capability_manifest["capabilities"]
            for category in ("required", "optional")
            for name in capability["tools"].get(category, [])
        }
    )
    version_args = {
        "7z": ("i",),
        "ffmpeg": ("-version",),
        "ffprobe": ("-version",),
        "libreoffice": ("--version",),
        "qpdf": ("--version",),
    }
    observed = {}
    for name in names:
        if name == "Pillow format plugins":
            try:
                pillow_version = importlib.metadata.version("Pillow")
            except importlib.metadata.PackageNotFoundError:
                pillow_version = None
            observed[name] = {
                "available": pillow_version is not None,
                "resolved_path": None,
                "version": pillow_version,
                "error": None if pillow_version is not None else "not_found",
                "policy_id": "python-runtime-v1",
            }
            continue
        executables = ("libreoffice", "soffice") if name == "libreoffice" else (name,)
        records = [
            probe_tool(
                executable,
                version_args=version_args.get(executable, ("--version",)),
                policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=64 * 1024),
            )
            for executable in executables
        ]
        record = next((candidate for candidate in records if candidate.available), records[0])
        observed[name] = {
            "available": record.available,
            "executable_name": record.name,
            "attempted_executables": list(executables),
            "resolved_path": record.resolved_path,
            "version": record.version,
            "error": record.error,
            "policy_id": "bounded-v1",
        }
    return {"declared": names, "observed": observed, "capability_quality_gate": capability_manifest["quality_gate"]}


def _redaction_roots(args: argparse.Namespace, input_root: Path, output_root: Path | None, layout: WorkspaceLayout) -> list[Path]:
    if not args.redact_paths:
        return []
    roots = [input_root, layout.root, layout.db_path.parent]
    if output_root is not None:
        roots.append(output_root)
    return roots


def _emit(writer: MachineEventWriter, conn, run_id: int, event: str, payload: dict[str, Any], *, file_id: int | None = None) -> None:
    record = writer.emit(event, payload)
    insert_event(
        conn,
        run_id,
        event,
        dict(record["payload"]),
        sequence=int(record["sequence"]),
        file_id=file_id,
    )


def _start_persisted_run(
    conn,
    args: argparse.Namespace,
    command: str,
    input_root: Path,
    output_root: Path | None,
    layout: WorkspaceLayout,
    config: dict[str, Any],
    goals: Iterable[RecoveryGoal],
    capability_manifest: dict[str, Any],
) -> int:
    run_id = start_run(
        conn,
        command,
        input_root,
        output_root,
        args.engine,
        workspace_root=layout.root,
        config=config,
        goals=[goal.value for goal in goals],
        application_version=__version__,
        platform=_platform_evidence(),
        tools=_tool_evidence(capability_manifest),
        resume_of_run_id=getattr(args, "resume", None),
        database_path=layout.db_path,
    )
    layout.write_config_snapshot(run_id, config)
    return run_id


def _event_writer(args: argparse.Namespace, run_id: int, layout: WorkspaceLayout, roots: list[Path]) -> MachineEventWriter:
    path = Path(args.events).resolve() if args.events else layout.reports_dir / f"run-{run_id:06d}.events.jsonl"
    return MachineEventWriter(path, redact_roots=roots, redaction_salt=args.redaction_salt)


def _default_manifest(args: argparse.Namespace, run_id: int, layout: WorkspaceLayout) -> Path:
    selected = getattr(args, "manifest", None) or getattr(args, "output_json", None)
    return Path(selected).resolve() if selected else layout.reports_dir / f"run-{run_id:06d}.manifest.json"


def _write_run_reports(conn, run_id: int, args: argparse.Namespace, layout: WorkspaceLayout, roots: list[Path]) -> None:
    write_json_report(
        conn,
        run_id,
        _default_manifest(args, run_id, layout),
        redact_roots=roots,
        redaction_salt=args.redaction_salt,
    )
    if getattr(args, "output_csv", None):
        write_attempts_csv(
            conn,
            run_id,
            Path(args.output_csv).resolve(),
            redact_roots=roots,
            redaction_salt=args.redaction_salt,
        )
    if getattr(args, "output_text", None):
        write_text_report(
            conn,
            run_id,
            Path(args.output_text).resolve(),
            redact_roots=roots,
            redaction_salt=args.redaction_salt,
        )


def command_capabilities(args: argparse.Namespace) -> int:
    configure_process_isolation(required=False, wrapper=None)
    payload = capability_json() if args.format == "json" else capability_markdown() if args.format == "markdown" else capability_text()
    if args.output:
        write_capability_manifest(Path(args.output).resolve(), format=args.format)
    else:
        sys.stdout.write(payload)
    return EXIT_OK


def _run_analysis_command(args: argparse.Namespace, command: str, *, classify: bool) -> int:
    limits = _limits_from_args(args)
    configure_process_isolation(required=False, wrapper=None)
    pipeline = RecoveryPipeline(engine_name=args.engine, limits=limits)
    capabilities = build_capability_manifest(pipeline.handlers)
    input_root, _, layout = _prepare_layout(args, None)
    layout.ensure()
    cancellation = CancellationToken(args.cancel_marker)
    config = _effective_config(args, limits)
    failures = 0
    with connect(layout.db_path) as conn:
        run_id = _start_persisted_run(conn, args, command, input_root, None, layout, config, (), capabilities)
        roots = _redaction_roots(args, input_root, None, layout)
        writer = _event_writer(args, run_id, layout, roots)
        _emit(writer, conn, run_id, "run.created", {"command": command, "input_root": str(input_root)})
        transition_run(conn, run_id, "running")
        _emit(writer, conn, run_id, "run.running", {"workers": limits.max_workers})
        for analysis in pipeline.analyze_paths(
            input_root,
            recursive=args.recursive,
            all_files=args.all_files,
            classify=classify,
            limits=limits,
            cancellation=cancellation,
            complete_limit=args.complete_limit,
        ):
            if analysis.record is None:
                failures += 1
                _emit(writer, conn, run_id, "file.failed", {"path": str(analysis.path), "error_code": analysis.error_code, "error": analysis.error_detail})
                conn.commit()
                continue
            with file_transaction(conn, f"analysis_{analysis.record.relative_path}"):
                file_id = pipeline.persist_analysis(conn, run_id, analysis)
                _emit(
                    writer,
                    conn,
                    run_id,
                    "file.classified" if classify else "file.scanned",
                    {
                        "relative_path": str(analysis.record.relative_path),
                        "sha256": analysis.record.sha256,
                        "family": analysis.classification.family if analysis.classification else None,
                    },
                    file_id=file_id,
                )
                for budget in analysis.budget_events:
                    _emit(
                        writer,
                        conn,
                        run_id,
                        f"budget.{budget.get('outcome', 'observed')}",
                        {"relative_path": str(analysis.record.relative_path), **budget},
                        file_id=file_id,
                    )
            conn.commit()
            if not args.quiet:
                label = analysis.classification.family if analysis.classification else analysis.record.byte0_kind
                print(f"{command.upper():8} {analysis.record.relative_path} [{label}]", file=sys.stderr)
        if cancellation.cancelled:
            transition_run(conn, run_id, "cancelled", cancellation_reason=cancellation.reason)
            final_state = "cancelled"
        elif failures:
            transition_run(conn, run_id, "partial")
            final_state = "partial"
        else:
            transition_run(conn, run_id, "completed")
            final_state = "completed"
        _emit(writer, conn, run_id, f"run.{final_state}", {"unpersisted_failures": failures})
        _write_run_reports(conn, run_id, args, layout, roots)
        summary = fetch_summary(conn, run_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return EXIT_FATAL if final_state == "cancelled" else EXIT_PARTIAL if failures else EXIT_OK


def command_scan(args: argparse.Namespace) -> int:
    return _run_analysis_command(args, "scan", classify=False)


def command_classify(args: argparse.Namespace) -> int:
    return _run_analysis_command(args, "classify", classify=True)


def _verify_resume_compatibility(previous, *, input_root: Path, output_root: Path, config: dict[str, Any]) -> None:
    previous_input = Path(str(previous["input_root"])).resolve() if previous["input_root"] else None
    previous_output = Path(str(previous["output_root"])).resolve() if previous["output_root"] else None
    if previous_input != input_root or previous_output != output_root:
        raise ValueError("resume requires the same canonical input and output roots")
    previous_config = json.loads(previous["config_json"] or "{}")
    if previous_config != config:
        raise ValueError("resume requires the same effective configuration and goals")


def _persist_execution(conn, pipeline: RecoveryPipeline, run_id: int, execution: FileExecution) -> int | None:
    key = execution.record.relative_path if execution.record else execution.analysis.path.name
    with file_transaction(conn, f"recover_{key}"):
        return pipeline.persist_execution(conn, run_id, execution)


def _human_result(execution: FileExecution) -> str:
    relative = execution.record.relative_path if execution.record else execution.analysis.path.name
    artifacts = len(execution.artifacts)
    return f"{execution.status.upper():16} {relative} | artifacts={artifacts}"


def _emit_execution_evidence(
    writer: MachineEventWriter,
    conn,
    run_id: int,
    execution: FileExecution,
    *,
    file_id: int | None,
) -> None:
    relative = str(execution.record.relative_path) if execution.record else str(execution.analysis.path)
    for budget in execution.budget_events:
        _emit(writer, conn, run_id, f"budget.{budget.get('outcome', 'observed')}", {"relative_path": relative, **budget}, file_id=file_id)
    for goal in execution.goals:
        if goal.outcome.candidate is not None:
            _emit(
                writer,
                conn,
                run_id,
                "candidate.selected",
                {
                    "relative_path": relative,
                    "goal": goal.goal,
                    "strategy_id": goal.outcome.candidate.strategy_id,
                    "content_hash": goal.outcome.candidate.dedupe_hash,
                    "strategy_links": len(goal.outcome.candidate.strategy_links),
                },
                file_id=file_id,
            )
        tool = goal.outcome.decode.telemetry.get("tool")
        if isinstance(tool, dict) and tool:
            _emit(writer, conn, run_id, "tool.observed", {"relative_path": relative, "goal": goal.goal, "handler_id": goal.handler_id, "evidence": tool}, file_id=file_id)
        for artifact in goal.outcome.artifacts:
            _emit(
                writer,
                conn,
                run_id,
                "artifact.published",
                {
                    "relative_path": relative,
                    "goal": goal.goal,
                    "type": artifact.artifact_type,
                    "path": str(artifact.path),
                    "sha256": artifact.sha256,
                    "size": artifact.size,
                    "fidelity_grade": artifact.fidelity_grade,
                    "validation_state": artifact.validation_state,
                },
                file_id=file_id,
            )
        _emit(
            writer,
            conn,
            run_id,
            "goal.completed",
            {
                "relative_path": relative,
                "goal": goal.goal,
                "handler_id": goal.handler_id,
                "plan_id": goal.plan.plan_id if goal.plan else None,
                "outcome_grade": goal.outcome.grade,
                "ok": goal.outcome.decode.ok,
                "error": goal.outcome.decode.error,
            },
            file_id=file_id,
        )
    _emit(
        writer,
        conn,
        run_id,
        f"file.{execution.status}",
        {
            "relative_path": relative,
            "status": execution.status,
            "artifact_count": len(execution.artifacts),
            "error_code": execution.error_code,
            "error": execution.error_detail,
        },
        file_id=file_id,
    )


def _exit_for_summary(summary: dict[str, Any], policy: str, final_state: str) -> int:
    if final_state in {"failed", "cancelled"}:
        return EXIT_FATAL
    if int(summary["total_files"]) == 0:
        return EXIT_NO_RESULTS if policy != "report-only" else EXIT_OK
    adverse = int(summary["failed"]) + int(summary["partial"])
    if policy == "report-only":
        return EXIT_OK
    if policy == "partial-ok":
        return EXIT_OK if int(summary["recovered"]) + int(summary["partial"]) > 0 else EXIT_PARTIAL
    return EXIT_OK if adverse == 0 and final_state == "completed" else EXIT_PARTIAL


def _run_recovery(args: argparse.Namespace, command: str) -> int:
    limits = _limits_from_args(args)
    goals = _goals(args)
    configure_process_isolation(required=args.require_tool_isolation, wrapper=args.isolation_wrapper)
    pipeline = RecoveryPipeline(engine_name=args.engine, limits=limits)
    capabilities = build_capability_manifest(pipeline.handlers)
    input_root, output_root, layout = _prepare_layout(args, args.output_root)
    assert output_root is not None
    ground_truth: dict[str, Any] | None = None
    supplied_ground_truth = getattr(args, "ground_truth", None)
    if supplied_ground_truth is not None:
        ground_truth_path = Path(supplied_ground_truth).resolve(strict=True)
        if _is_within(ground_truth_path, input_root):
            raise PathLayoutError("ground-truth metadata must be outside input_root so it cannot be recovered as input")
        ground_truth = load_ground_truth(ground_truth_path)
    layout.ensure()
    cancellation = CancellationToken(args.cancel_marker)
    config = _effective_config(args, limits, goals, ground_truth=ground_truth)
    statuses: list[str] = []
    unpersisted_failures = 0
    fatal_error: str | None = None

    with connect(layout.db_path) as conn:
        resume_rows = None
        if args.resume:
            previous = fetch_run(conn, args.resume)
            _verify_resume_compatibility(previous, input_root=input_root, output_root=output_root, config=config)
            resume_rows = fetch_resume_files(conn, args.resume)
        run_id = _start_persisted_run(conn, args, command, input_root, output_root, layout, config, goals, capabilities)
        roots = _redaction_roots(args, input_root, output_root, layout)
        writer = _event_writer(args, run_id, layout, roots)
        _emit(writer, conn, run_id, "run.created", {"command": command, "input_root": str(input_root), "output_root": str(output_root), "goals": [goal.value for goal in goals], "resume_of": args.resume})
        transition_run(conn, run_id, "running")
        _emit(writer, conn, run_id, "run.running", {"workers": limits.max_workers, "limits": asdict(limits)})
        conn.commit()
        memory_sampler = ProcessMemorySampler() if command == "benchmark" else None
        if memory_sampler is not None:
            memory_sampler.start()

        try:
            if resume_rows is None:
                executions = pipeline.process_paths(
                    input_root,
                    output_root=output_root,
                    recursive=args.recursive,
                    all_files=args.all_files,
                    goals=goals,
                    limits=limits,
                    cancellation=cancellation,
                    complete_limit=args.complete_limit,
                    save_raw_candidates=args.save_raw_candidates,
                )
                for execution in executions:
                    file_id = _persist_execution(conn, pipeline, run_id, execution)
                    statuses.append(execution.status)
                    _emit_execution_evidence(writer, conn, run_id, execution, file_id=file_id)
                    conn.commit()
                    if not args.quiet:
                        print(_human_result(execution), file=sys.stderr)
            else:
                analyses = pipeline.analyze_paths(
                    input_root,
                    recursive=args.recursive,
                    all_files=args.all_files,
                    classify=True,
                    limits=limits,
                    cancellation=cancellation,
                    complete_limit=args.complete_limit,
                )
                for analysis in analyses:
                    if analysis.record is None:
                        unpersisted_failures += 1
                        _emit(writer, conn, run_id, "file.failed", {"path": str(analysis.path), "error_code": analysis.error_code, "error": analysis.error_detail})
                        conn.commit()
                        continue
                    prior = resume_rows.get(str(analysis.record.relative_path))
                    unchanged = prior is not None and source_identity_matches(prior, analysis.record)
                    already_complete = unchanged and str(prior["status"]) in {"recovered", "partial", "skipped"}
                    if already_complete:
                        with file_transaction(conn, f"resume_{analysis.record.relative_path}"):
                            file_id = pipeline.persist_analysis(conn, run_id, analysis)
                            assert file_id is not None
                            transition_file(conn, file_id, "skipped", error_code="resumed_unchanged", error_detail=f"reused evidence from run {args.resume}")
                        statuses.append("skipped")
                        _emit(writer, conn, run_id, "file.skipped", {"relative_path": str(analysis.record.relative_path), "reason": "resumed_unchanged", "prior_run_id": args.resume}, file_id=file_id)
                        conn.commit()
                        continue
                    if prior is not None and not unchanged and args.changed_input_policy != "reprocess":
                        with file_transaction(conn, f"changed_{analysis.record.relative_path}"):
                            file_id = pipeline.persist_analysis(conn, run_id, analysis)
                            assert file_id is not None
                            transition_file(conn, file_id, "failed" if args.changed_input_policy == "abort" else "skipped", error_code="resume_input_changed", error_detail=args.changed_input_policy)
                        statuses.append("failed" if args.changed_input_policy == "abort" else "skipped")
                        _emit(writer, conn, run_id, "file.changed", {"relative_path": str(analysis.record.relative_path), "policy": args.changed_input_policy}, file_id=file_id)
                        conn.commit()
                        if args.changed_input_policy == "abort":
                            raise RuntimeError(f"resume input changed: {analysis.record.relative_path}")
                        continue
                    resume_output_root = output_root / "_resumed" / f"run-{run_id:06d}"
                    execution = pipeline.process_path(
                        input_root,
                        analysis.path,
                        output_root=resume_output_root,
                        goals=goals,
                        limits=limits,
                        cancellation=cancellation,
                        save_raw_candidates=args.save_raw_candidates,
                    )
                    file_id = _persist_execution(conn, pipeline, run_id, execution)
                    statuses.append(execution.status)
                    _emit_execution_evidence(writer, conn, run_id, execution, file_id=file_id)
                    conn.commit()
                    if not args.quiet:
                        print(_human_result(execution), file=sys.stderr)
        except Exception as exc:
            fatal_error = f"{exc.__class__.__name__}: {exc}"

        benchmark_observation: dict[str, Any] | None = None
        if memory_sampler is not None:
            benchmark_observation = {"memory": memory_sampler.stop()}
            if ground_truth is not None:
                try:
                    benchmark_observation["ground_truth"] = evaluate_ground_truth(conn, run_id, ground_truth)
                except Exception as exc:
                    benchmark_observation["ground_truth_error"] = f"{exc.__class__.__name__}: {exc}"
                    if fatal_error is None:
                        fatal_error = f"ground-truth evaluation failed: {exc.__class__.__name__}: {exc}"

        if cancellation.cancelled:
            transition_run(conn, run_id, "cancelled", cancellation_reason=cancellation.reason)
            final_state = "cancelled"
        elif fatal_error:
            transition_run(conn, run_id, "failed", fatal_error=fatal_error)
            final_state = "failed"
        elif unpersisted_failures or any(status not in {"recovered", "skipped"} for status in statuses):
            transition_run(conn, run_id, "partial")
            final_state = "partial"
        else:
            transition_run(conn, run_id, "completed")
            final_state = "completed"
        if benchmark_observation is not None:
            _emit(writer, conn, run_id, "benchmark.observed", benchmark_observation)
        _emit(writer, conn, run_id, f"run.{final_state}", {"statuses": statuses, "unpersisted_failures": unpersisted_failures, "fatal_error": fatal_error})
        _write_run_reports(conn, run_id, args, layout, roots)
        summary = fetch_summary(conn, run_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return _exit_for_summary(summary, args.exit_policy, final_state)


def command_recover(args: argparse.Namespace) -> int:
    return _run_recovery(args, "recover")


def command_benchmark(args: argparse.Namespace) -> int:
    return _run_recovery(args, "benchmark")


def command_report(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve(strict=True)
    with connect(db_path) as conn:
        run_id = args.run_id or latest_run_id(conn)
        if run_id is None:
            raise ValueError("no runs found")
        run = fetch_run(conn, run_id)
        roots: list[Path] = []
        input_root = Path(str(run["input_root"])).resolve() if run["input_root"] else None
        for selected in (args.output_json, args.output_csv, args.output_text):
            if selected is not None and input_root is not None and _is_within(Path(selected), input_root):
                raise PathLayoutError(f"report path overlaps the persisted input root: {selected}")
        if args.redact_paths:
            roots = [Path(value) for value in (run["input_root"], run["output_root"], run["workspace_root"]) if value]
        if args.output_json:
            write_json_report(conn, run_id, Path(args.output_json).resolve(), redact_roots=roots, redaction_salt=args.redaction_salt)
        if args.output_csv:
            write_attempts_csv(conn, run_id, Path(args.output_csv).resolve(), redact_roots=roots, redaction_salt=args.redaction_salt)
        if args.output_text:
            write_text_report(conn, run_id, Path(args.output_text).resolve(), redact_roots=roots, redaction_salt=args.redaction_salt)
        summary = fetch_summary(conn, run_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "capabilities": command_capabilities,
        "scan": command_scan,
        "classify": command_classify,
        "recover": command_recover,
        "benchmark": command_benchmark,
        "report": command_report,
    }
    try:
        return handlers[args.command](args)
    except (CollisionError, PathLayoutError, ValueError, OSError, RuntimeError) as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        return EXIT_FATAL


if __name__ == "__main__":
    raise SystemExit(main())
