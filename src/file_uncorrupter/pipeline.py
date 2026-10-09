from __future__ import annotations

import mimetypes
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from functools import partial
from pathlib import Path
from typing import Callable, Iterable, Iterator

from .atomic import AtomicArtifactWriter, CollisionError, ValidationError
from .budgets import BudgetExceeded, BudgetTracker, ResourceLimits
from .byte_source import FileByteSource, SourceChangedError, UnsafeSourceError
from .cancellation import CancelledError, CancellationToken
from .classification import classify_record
from .constants import IMAGE_OUTPUT_EXT, VIDEO_KINDS
from .db import (
    insert_archive_members,
    insert_artifact_relation,
    insert_attempt,
    insert_budget_event,
    insert_candidate,
    insert_document_parts,
    insert_file,
    insert_media_streams,
    insert_output,
    insert_text_spans,
    insert_tool_record,
    transition_file,
)
from .decoders import (
    ffmpeg_available,
    normalized_video_output_path,
    probe_video_with_ffmpeg,
    probe_with_ffmpeg,
    probe_with_pillow,
    recover_video_with_ffmpeg,
    save_with_ffmpeg,
    save_with_pillow,
    sha256_path,
)
from .engines import build_registry
from .handlers.base import HandlerContext, InspectionResult, RecoveryGoal
from .handlers.registry import HandlerRegistry, build_handler_registry
from .intake import build_file_record, build_file_record_from_source, iter_input_files, read_bytes
from .paths import PathLayoutError, contained_path
from .scoring import score_candidate
from .types import Artifact, Candidate, CandidatePlan, Classification, DecodeResult, FileRecord, OutcomeGrade, RecoveryOutcome


def _image_output_kind(record: FileRecord, classification: Classification) -> str:
    if record.declared_kind and record.declared_kind not in VIDEO_KINDS:
        return record.declared_kind
    if record.byte0_kind != "unknown" and record.byte0_kind not in VIDEO_KINDS:
        return record.byte0_kind
    if classification.family != "unknown" and classification.family not in VIDEO_KINDS:
        return classification.family
    return "png"


def _coalesce_budget_events(events: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    latest: dict[tuple[str, str, str], dict[str, object]] = {}
    for event in events:
        key = (
            str(event.get("scope") or "file"),
            str(event.get("name") or "unknown"),
            str(event.get("outcome") or "unknown"),
        )
        latest[key] = dict(event)
    return [latest[key] for key in sorted(latest)]


@dataclass(slots=True)
class FileAnalysis:
    path: Path
    record: FileRecord | None = None
    classification: Classification | None = None
    budget_events: list[dict[str, object]] = field(default_factory=list)
    error_code: str | None = None
    error_detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.record is not None and self.error_code is None


@dataclass(slots=True)
class GoalExecution:
    goal: str
    handler_id: str
    plan: CandidatePlan | None
    outcome: RecoveryOutcome


@dataclass(slots=True)
class FileExecution:
    analysis: FileAnalysis
    inspection: InspectionResult | None = None
    goals: list[GoalExecution] = field(default_factory=list)
    budget_events: list[dict[str, object]] = field(default_factory=list)
    error_code: str | None = None
    error_detail: str | None = None

    @property
    def record(self) -> FileRecord | None:
        return self.analysis.record

    @property
    def classification(self) -> Classification | None:
        return self.analysis.classification

    @property
    def status(self) -> str:
        if self.error_code == "cancelled":
            return "cancelled"
        if self.error_code == "budget_exceeded":
            return "budget_exceeded"
        if self.error_code == "dependency_unavailable":
            return "unavailable"
        if self.error_code:
            return "failed"
        grades = [item.outcome.grade for item in self.goals]
        if any(grade in {OutcomeGrade.VALIDATED_ORIGINAL.value, OutcomeGrade.VALIDATED_NORMALIZED.value} for grade in grades):
            return "recovered"
        if any(grade in {OutcomeGrade.PARTIAL_CONTENT.value, OutcomeGrade.PREVIEW_ONLY.value} for grade in grades):
            return "partial"
        if grades and all(grade == OutcomeGrade.UNAVAILABLE_DEPENDENCY.value for grade in grades):
            return "unavailable"
        if grades and all(grade == OutcomeGrade.BUDGET_EXCEEDED.value for grade in grades):
            return "budget_exceeded"
        if grades and all(grade == OutcomeGrade.CANCELLED.value for grade in grades):
            return "cancelled"
        return "failed"

    @property
    def artifacts(self) -> list[Artifact]:
        return [artifact for item in self.goals for artifact in item.outcome.artifacts]


class RecoveryPipeline:
    def __init__(
        self,
        engine_name: str = "baseline-v2",
        *,
        max_ffmpeg_candidates: int = 12,
        limits: ResourceLimits | None = None,
        handlers: HandlerRegistry | None = None,
    ) -> None:
        registry = build_registry()
        if engine_name not in registry:
            raise ValueError(f"Unknown engine: {engine_name}")
        self.engine = registry[engine_name]
        self.engine_name = engine_name
        self.max_ffmpeg_candidates = max_ffmpeg_candidates
        self.limits = limits or ResourceLimits()
        self.handlers = handlers or build_handler_registry()

    def scan_records(self, input_root: Path, recursive: bool, all_files: bool) -> list[tuple[FileRecord, bytes]]:
        records: list[tuple[FileRecord, bytes]] = []
        for path in iter_input_files(input_root, recursive=recursive, all_files=all_files):
            data = read_bytes(path)
            record = build_file_record(input_root, path, data)
            records.append((record, data))
        return records

    def classify_records(self, records: Iterable[tuple[FileRecord, bytes]]) -> list[tuple[FileRecord, bytes, Classification]]:
        result: list[tuple[FileRecord, bytes, Classification]] = []
        for record, data in records:
            classification = classify_record(record, data)
            result.append((record, data, classification))
        return result

    def recover_one(
        self,
        record: FileRecord,
        data: bytes,
        classification: Classification,
        output_root: Path,
        save_raw_candidates: bool,
    ) -> tuple[RecoveryOutcome, Path | None]:
        try:
            if sha256_path(record.path) != record.sha256:
                decode = DecodeResult(ok=False, decoder="none", error="source_changed_before_recovery")
                return RecoveryOutcome(candidate=None, decode=decode, attempts=[], grade="failed"), None
        except OSError as exc:
            decode = DecodeResult(ok=False, decoder="none", error=f"source_unavailable:{exc.__class__.__name__}")
            return RecoveryOutcome(candidate=None, decode=decode, attempts=[], grade="failed"), None
        if classification.family not in self.engine.families:
            decode = DecodeResult(ok=False, decoder="none", error=f"no_engine_for_family:{classification.family}")
            return RecoveryOutcome(candidate=None, decode=decode, attempts=[]), None

        candidates = self.engine.generate_candidates(record, data, classification)
        best_candidate: Candidate | None = None
        best_probe: DecodeResult | None = None
        best_attempt_phase = "probe"
        attempts: list[dict[str, object]] = []
        probe_cache: dict[tuple[str, str], DecodeResult] = {}

        for candidate in candidates:
            if classification.family in VIDEO_KINDS:
                cache_key = ("video", candidate.dedupe_hash)
                if cache_key not in probe_cache:
                    probe_cache[cache_key] = probe_video_with_ffmpeg(candidate.data, candidate.family)
                probe = replace(probe_cache[cache_key])
                phase = "video_probe"
            else:
                cache_key = ("pillow", candidate.dedupe_hash)
                if cache_key not in probe_cache:
                    probe_cache[cache_key] = probe_with_pillow(candidate.data)
                probe = replace(probe_cache[cache_key])
                phase = "image_probe"
            probe.score = score_candidate(candidate, probe, classification)
            attempts.append(
                {
                    "candidate": candidate,
                    "decoder": probe.decoder,
                    "phase": phase,
                    "ok": probe.ok,
                    "width": probe.width,
                    "height": probe.height,
                    "mode": probe.mode,
                    "decoded_format": probe.decoded_format,
                    "duration_ms": probe.duration_ms,
                    "frame_count": probe.frame_count,
                    "score": probe.score,
                    "error": probe.error,
                    "telemetry": probe.telemetry,
                }
            )
            if probe.ok and (best_probe is None or probe.score > best_probe.score):
                best_candidate = candidate
                best_probe = probe
                best_attempt_phase = phase

        if classification.family not in VIDEO_KINDS and ffmpeg_available() and best_candidate is None:
            for candidate in candidates[: self.max_ffmpeg_candidates]:
                cache_key = ("ffmpeg", candidate.dedupe_hash)
                if cache_key not in probe_cache:
                    probe_cache[cache_key] = probe_with_ffmpeg(candidate.data, candidate.family)
                ffmpeg_probe = replace(probe_cache[cache_key])
                ffmpeg_probe.score = score_candidate(candidate, ffmpeg_probe, classification)
                attempts.append(
                    {
                        "candidate": candidate,
                        "decoder": ffmpeg_probe.decoder,
                        "phase": "image_probe_ffmpeg",
                        "ok": ffmpeg_probe.ok,
                        "width": ffmpeg_probe.width,
                        "height": ffmpeg_probe.height,
                        "mode": ffmpeg_probe.mode,
                        "decoded_format": ffmpeg_probe.decoded_format,
                        "duration_ms": ffmpeg_probe.duration_ms,
                        "frame_count": ffmpeg_probe.frame_count,
                        "score": ffmpeg_probe.score,
                        "error": ffmpeg_probe.error,
                        "telemetry": ffmpeg_probe.telemetry,
                    }
                )
                if ffmpeg_probe.ok and (best_probe is None or ffmpeg_probe.score > best_probe.score):
                    best_candidate = candidate
                    best_probe = ffmpeg_probe
                    best_attempt_phase = "image_probe_ffmpeg"

        if best_candidate is None or best_probe is None or not best_probe.ok:
            decode = DecodeResult(ok=False, decoder="none", error="no_candidate_succeeded")
            return RecoveryOutcome(candidate=None, decode=decode, attempts=attempts), None

        raw_candidate_path: Path | None = None
        artifacts: list[Artifact] = []
        final_attempt_phase = best_attempt_phase + "_final"

        if classification.family in VIDEO_KINDS:
            output_path = normalized_video_output_path(output_root, record.relative_path, classification.family)
            final, artifacts = recover_video_with_ffmpeg(best_candidate.data, best_candidate.family, output_path)
        else:
            output_kind = _image_output_kind(record, classification)
            suffix = IMAGE_OUTPUT_EXT.get(output_kind, ".png")
            output_path = contained_path(output_root, record.relative_path.with_suffix(suffix))
            final = save_with_pillow(best_candidate.data, output_path, output_kind)
            if not final.ok and ffmpeg_available():
                final = save_with_ffmpeg(best_candidate.data, best_candidate.family, output_path, output_kind)
            if final.ok and final.output_path is not None and final.output_path.exists():
                artifacts = [
                    Artifact(
                        artifact_type="image",
                        path=final.output_path,
                        sha256=sha256_path(final.output_path),
                        decoder=final.decoder,
                        width=final.width,
                        height=final.height,
                        size=final.output_path.stat().st_size,
                        media_type=f"image/{'jpeg' if output_kind == 'jpeg' else output_kind}",
                        fidelity_grade="validated_normalized",
                        validation_state="decoder_validated",
                        published=True,
                    )
                ]
        final.score = score_candidate(best_candidate, final, classification) if final.ok else float("-inf")

        if final.ok and save_raw_candidates:
            raw_relative = Path("_raw_candidates") / record.relative_path
            raw_relative = raw_relative.with_suffix(raw_relative.suffix + ".candidate")
            raw_candidate_path = AtomicArtifactWriter(output_root).publish_bytes(raw_relative, best_candidate.data).path

        if final.ok and sha256_path(record.path) != record.sha256:
            final = DecodeResult(ok=False, decoder=final.decoder, error="source_changed_during_recovery")

        attempts.append(
            {
                "candidate": best_candidate,
                "decoder": final.decoder,
                "phase": final_attempt_phase,
                "ok": final.ok,
                "width": final.width,
                "height": final.height,
                "mode": final.mode,
                "decoded_format": final.decoded_format,
                "duration_ms": final.duration_ms,
                "frame_count": final.frame_count,
                "score": final.score,
                "error": final.error,
                "telemetry": final.telemetry,
            }
        )

        return RecoveryOutcome(candidate=best_candidate, decode=final, attempts=attempts, artifacts=artifacts), raw_candidate_path

    def persist_scan(self, conn, run_id: int, classified: list[tuple[FileRecord, bytes, Classification]]) -> list[tuple[int, FileRecord, bytes, Classification]]:
        rows: list[tuple[int, FileRecord, bytes, Classification]] = []
        for record, data, classification in classified:
            file_id = insert_file(conn, run_id, record, classification)
            rows.append((file_id, record, data, classification))
        return rows

    def persist_recovery(self, conn, run_id: int, file_id: int, outcome: RecoveryOutcome, raw_candidate_path: Path | None) -> None:
        transition_file(conn, file_id, "processing")
        winning_attempt_id: int | None = None
        for attempt in outcome.attempts:
            candidate = attempt.get("candidate")
            candidate_id = None
            if isinstance(candidate, Candidate):
                candidate_id = insert_candidate(conn, run_id, file_id, candidate)
            decode = DecodeResult(
                ok=bool(attempt["ok"]),
                decoder=str(attempt["decoder"]),
                width=int(attempt.get("width") or 0),
                height=int(attempt.get("height") or 0),
                mode=str(attempt.get("mode") or ""),
                decoded_format=str(attempt.get("decoded_format") or ""),
                duration_ms=int(attempt.get("duration_ms") or 0),
                frame_count=int(attempt.get("frame_count") or 0),
                score=float(attempt.get("score") or float("-inf")),
                error=str(attempt.get("error") or ""),
                telemetry=dict(attempt.get("telemetry") or {}),
            )
            attempt_id = insert_attempt(conn, run_id, file_id, candidate_id, decode, phase=str(attempt.get("phase") or "probe"))
            if outcome.candidate is not None and isinstance(candidate, Candidate) and candidate.dedupe_hash == outcome.candidate.dedupe_hash and str(attempt.get("phase") or "").endswith("_final"):
                winning_attempt_id = attempt_id

        if outcome.decode.ok:
            if outcome.artifacts:
                for artifact in outcome.artifacts:
                    insert_output(conn, run_id, file_id, winning_attempt_id, outcome.candidate, outcome.decode, artifact, raw_candidate_path)
            else:
                insert_output(conn, run_id, file_id, winning_attempt_id, outcome.candidate, outcome.decode, None, raw_candidate_path)
        else:
            insert_output(conn, run_id, file_id, winning_attempt_id, outcome.candidate, outcome.decode, None, raw_candidate_path)
        if outcome.decode.ok:
            transition_file(conn, file_id, "recovered")
        elif "budget" in outcome.decode.error:
            transition_file(conn, file_id, "budget_exceeded", error_code="budget_exceeded", error_detail=outcome.decode.error)
        elif "cancel" in outcome.decode.error:
            transition_file(conn, file_id, "cancelled", error_code="cancelled", error_detail=outcome.decode.error)
        elif "not_found" in outcome.decode.error or "unavailable" in outcome.decode.error:
            transition_file(conn, file_id, "unavailable", error_code="dependency_unavailable", error_detail=outcome.decode.error)
        else:
            transition_file(conn, file_id, "failed", error_code="recovery_failed", error_detail=outcome.decode.error)

    @staticmethod
    def _failure_outcome(error: str, grade: str = OutcomeGrade.FAILED.value, *, decoder: str = "none") -> RecoveryOutcome:
        return RecoveryOutcome(
            candidate=None,
            decode=DecodeResult(ok=False, decoder=decoder, error=error),
            grade=grade,
            diagnostics=[{"error": error}],
        )

    @staticmethod
    def _analysis_error(path: Path, exc: Exception, budget_events: list[dict[str, object]]) -> FileAnalysis:
        if isinstance(exc, CancelledError):
            code = "cancelled"
        elif isinstance(exc, BudgetExceeded):
            code = "budget_exceeded"
        elif isinstance(exc, SourceChangedError):
            code = "source_changed"
        elif isinstance(exc, (UnsafeSourceError, PathLayoutError)):
            code = "unsafe_source"
        elif isinstance(exc, PermissionError):
            code = "inaccessible_source"
        elif isinstance(exc, OSError):
            code = "source_io_error"
        else:
            code = "analysis_failed"
        return FileAnalysis(path=path, budget_events=_coalesce_budget_events(budget_events), error_code=code, error_detail=str(exc))

    def analyze_path(
        self,
        input_root: Path,
        path: Path,
        *,
        classify: bool,
        limits: ResourceLimits | None = None,
        cancellation: CancellationToken | None = None,
    ) -> FileAnalysis:
        """Stream one immutable input into an inventory record and optional classification."""
        limits = limits or self.limits
        cancellation = cancellation or CancellationToken()
        budget_events: list[dict[str, object]] = []

        def record_budget(event: dict[str, object]) -> None:
            budget_events.append(dict(event))

        try:
            cancellation.checkpoint()
            scan_budget = BudgetTracker(
                limits.budget_limits(),
                scope=f"scan:{Path(path).name}",
                on_event=record_budget,
            )
            source = FileByteSource(path, limits=limits, budget=scan_budget)
            record = build_file_record_from_source(input_root, source)
            cancellation.checkpoint()
            classification = None
            if classify:
                sample_budget = BudgetTracker(
                    limits.budget_limits(),
                    scope=f"classify:{Path(path).name}",
                    on_event=record_budget,
                )
                sample_source = FileByteSource(path, limits=limits, budget=sample_budget)
                prefix_size = min(sample_source.size, limits.max_materialized_bytes, 4 * (1 << 20))
                sample = sample_source.prefix(prefix_size)
                tail_size = min(1 << 20, max(0, sample_source.size - prefix_size))
                if tail_size:
                    sample += sample_source.tail(tail_size)
                classification = classify_record(record, sample)
            return FileAnalysis(
                path=Path(path),
                record=record,
                classification=classification,
                budget_events=_coalesce_budget_events(budget_events),
            )
        except Exception as exc:
            return self._analysis_error(Path(path), exc, budget_events)

    def analyze_paths(
        self,
        input_root: Path,
        *,
        recursive: bool,
        all_files: bool,
        classify: bool,
        limits: ResourceLimits | None = None,
        cancellation: CancellationToken | None = None,
        complete_limit: int | None = None,
    ) -> Iterator[FileAnalysis]:
        limits = limits or self.limits
        cancellation = cancellation or CancellationToken()
        paths = list(iter_input_files(input_root, recursive=recursive, all_files=all_files))
        if complete_limit is not None:
            if complete_limit <= 0:
                raise ValueError("complete_limit must be greater than zero")
            paths = paths[:complete_limit]
        operation = partial(
            self.analyze_path,
            Path(input_root).resolve(strict=True),
            classify=classify,
            limits=limits,
            cancellation=cancellation,
        )
        if limits.max_workers == 1 or len(paths) <= 1:
            for path in paths:
                yield operation(path)
            return
        with ThreadPoolExecutor(max_workers=limits.max_workers, thread_name_prefix="uncorrupter-scan") as executor:
            yield from executor.map(operation, paths)

    @staticmethod
    def _artifact_type(path: Path, goal: str) -> str:
        lowered = path.name.lower()
        if any(marker in lowered for marker in ("diagnostic", "span-map", "manifest", "report")) or path.suffix.lower() in {".json", ".jsonl", ".csv"}:
            return "diagnostics"
        return {
            RecoveryGoal.REPAIR.value: "repaired",
            RecoveryGoal.NORMALIZE.value: "normalized",
            RecoveryGoal.EXTRACT.value: "extracted",
            RecoveryGoal.PREVIEW.value: "preview",
            RecoveryGoal.CARVE.value: "raw_fragment",
        }.get(goal, "extracted")

    @staticmethod
    def _plan_evidence(plan: CandidatePlan | None) -> dict[str, object] | None:
        if plan is None:
            return None
        return {
            "plan_id": plan.plan_id,
            "handler_id": plan.handler_id,
            "strategy_id": plan.strategy_id,
            "family": plan.family,
            "goal": plan.goal,
            "priority": plan.priority,
            "slices": [asdict(item) for item in plan.slices],
            "prepend_bytes": len(plan.prepend),
            "append_bytes": len(plan.append),
            "estimated_materialized_bytes": plan.estimated_materialized_bytes,
            "estimated_output_bytes": plan.estimated_output_bytes,
            "provenance": list(plan.provenance),
            "meta": plan.meta,
        }

    def _capture_artifacts(
        self,
        root: Path,
        before: set[Path],
        outcome: RecoveryOutcome,
        goal: str,
        budget: BudgetTracker,
    ) -> None:
        explicit = {artifact.path.resolve(): artifact for artifact in outcome.artifacts if artifact.path.exists()}
        current = {
            path.resolve()
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink() and ".uncorrupter-" not in path.name
        } if root.exists() else set()
        new_paths = sorted((current - before) | set(explicit), key=lambda item: item.as_posix().casefold())
        captured: list[Artifact] = []
        for path in new_paths:
            if path in explicit:
                artifact = explicit[path]
                if not artifact.size:
                    artifact.size = path.stat().st_size
                if not artifact.sha256:
                    artifact.sha256 = sha256_path(path)
                artifact.published = True
                artifact.meta.setdefault("goal", goal)
                captured.append(artifact)
                continue
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            captured.append(
                Artifact(
                    artifact_type=self._artifact_type(path, goal),
                    path=path,
                    sha256=sha256_path(path),
                    decoder=outcome.decode.decoder,
                    size=path.stat().st_size,
                    media_type=media_type,
                    fidelity_grade=outcome.grade,
                    validation_state="handler_validated" if outcome.decode.ok else "unverified",
                    published=True,
                    meta={"goal": goal, "captured_by": "pipeline"},
                )
            )
        outcome.artifacts = captured
        if captured and outcome.decode.output_path is None:
            outcome.decode.output_path = captured[0].path

    def process_path(
        self,
        input_root: Path,
        path: Path,
        *,
        output_root: Path,
        goals: Iterable[RecoveryGoal | str],
        limits: ResourceLimits | None = None,
        cancellation: CancellationToken | None = None,
        save_raw_candidates: bool = False,
    ) -> FileExecution:
        limits = limits or self.limits
        cancellation = cancellation or CancellationToken()
        normalized_goals = tuple(RecoveryGoal(goal) for goal in goals)
        if not normalized_goals:
            raise ValueError("at least one recovery goal is required")
        analysis = self.analyze_path(
            input_root,
            path,
            classify=True,
            limits=limits,
            cancellation=cancellation,
        )
        result = FileExecution(analysis=analysis, budget_events=list(analysis.budget_events))
        if not analysis.ok or analysis.record is None or analysis.classification is None:
            result.error_code = analysis.error_code or "analysis_failed"
            result.error_detail = analysis.error_detail or "source analysis did not produce a record"
            return result

        handlers = self.handlers.for_family(analysis.classification.family)
        if not handlers:
            result.error_code = "dependency_unavailable"
            result.error_detail = f"no registered handler for family {analysis.classification.family}"
            for goal in normalized_goals:
                result.goals.append(
                    GoalExecution(
                        goal=goal.value,
                        handler_id="none",
                        plan=None,
                        outcome=self._failure_outcome(
                            f"no_handler_for_family:{analysis.classification.family}",
                            OutcomeGrade.UNAVAILABLE_DEPENDENCY.value,
                        ),
                    )
                )
            return result

        inspection_cache: dict[str, InspectionResult] = {}
        for goal in normalized_goals:
            chosen_handler = None
            chosen_plan = None
            chosen_context = None
            goal_root: Path | None = None
            before: set[Path] = set()
            goal_budget_events: list[dict[str, object]] = []

            def record_budget(event: dict[str, object]) -> None:
                goal_budget_events.append(dict(event))

            try:
                cancellation.checkpoint()
                for handler in handlers:
                    goal_budget = BudgetTracker(
                        limits.budget_limits(),
                        scope=f"goal:{goal.value}:{analysis.record.relative_path}",
                        on_event=record_budget,
                    )
                    source = FileByteSource(path, limits=limits, budget=goal_budget)
                    goal_relative = analysis.record.relative_path.parent / f"{analysis.record.relative_path.name}.recovered" / goal.value
                    goal_output = contained_path(output_root, goal_relative)
                    context = HandlerContext(
                        source=source,
                        record=analysis.record,
                        classification=analysis.classification,
                        limits=limits,
                        budget=goal_budget,
                        cancellation=cancellation,
                        output_root=goal_output,
                    )
                    plans = sorted(handler.plan(context, goal), key=lambda plan: (-plan.priority, plan.plan_id))
                    if plans:
                        chosen_handler = handler
                        chosen_plan = plans[0]
                        chosen_context = context
                        goal_budget.consume("candidates", len(plans))
                        goal_budget.consume("candidate_bytes", max(0, chosen_plan.estimated_materialized_bytes))
                        break

                if chosen_handler is None or chosen_plan is None or chosen_context is None:
                    outcome = self._failure_outcome(
                        f"unsupported_or_unavailable_goal:{goal.value}",
                        OutcomeGrade.UNAVAILABLE_DEPENDENCY.value,
                    )
                    result.goals.append(GoalExecution(goal.value, handlers[0].handler_id, None, outcome))
                    result.budget_events.extend(_coalesce_budget_events(goal_budget_events))
                    continue

                if chosen_handler.handler_id not in inspection_cache:
                    inspect_budget = BudgetTracker(
                        limits.budget_limits(),
                        scope=f"inspect:{chosen_handler.handler_id}:{analysis.record.relative_path}",
                        on_event=record_budget,
                    )
                    inspect_source = FileByteSource(path, limits=limits, budget=inspect_budget)
                    inspect_context = HandlerContext(
                        source=inspect_source,
                        record=analysis.record,
                        classification=analysis.classification,
                        limits=limits,
                        budget=inspect_budget,
                        cancellation=cancellation,
                        output_root=None,
                    )
                    inspection_cache[chosen_handler.handler_id] = chosen_handler.inspect(inspect_context)
                    if result.inspection is None:
                        result.inspection = inspection_cache[chosen_handler.handler_id]

                goal_root = chosen_context.output_root
                assert goal_root is not None
                before = {
                    item.resolve()
                    for item in goal_root.rglob("*")
                    if item.is_file() and not item.is_symlink()
                } if goal_root.exists() else set()
                cancellation.checkpoint()
                outcome = chosen_handler.execute(chosen_context, chosen_plan)
                cancellation.checkpoint()
                if save_raw_candidates and outcome.candidate is not None:
                    raw = AtomicArtifactWriter(goal_root, budget=chosen_context.budget).publish_bytes(
                        "selected.raw-candidate",
                        outcome.candidate.data,
                    )
                    outcome.artifacts.append(
                        Artifact(
                            artifact_type="raw_fragment",
                            path=raw.path,
                            sha256=raw.sha256,
                            decoder=chosen_handler.handler_id,
                            size=raw.size,
                            media_type="application/octet-stream",
                            fidelity_grade=OutcomeGrade.PARTIAL_CONTENT.value,
                            validation_state="selected_candidate",
                            published=True,
                            meta={"explicitly_requested": True, "may_contain_source_content": True},
                        )
                    )
                self._capture_artifacts(goal_root, before, outcome, goal.value, chosen_context.budget)

                verification_budget = BudgetTracker(
                    limits.budget_limits(),
                    scope=f"verify:{goal.value}:{analysis.record.relative_path}",
                    on_event=record_budget,
                )
                verification_source = FileByteSource(path, limits=limits, budget=verification_budget)
                identity_changed = (
                    verification_source.identity.size != analysis.record.size
                    or verification_source.identity.mtime_ns != analysis.record.modified_ns
                    or verification_source.identity.device != analysis.record.device_id
                    or verification_source.identity.inode != analysis.record.inode_id
                )
                content_changed = verification_source.sha256() != analysis.record.sha256
                if identity_changed or content_changed:
                    outcome.decode.ok = False
                    outcome.decode.error = f"source_changed_during:{goal.value}"
                    outcome.grade = OutcomeGrade.FAILED.value
                    for artifact in outcome.artifacts:
                        artifact.validation_state = "source_changed"
                        artifact.fidelity_grade = OutcomeGrade.FAILED.value
                    result.goals.append(GoalExecution(goal.value, chosen_handler.handler_id, chosen_plan, outcome))
                    result.error_code = "source_changed"
                    result.error_detail = "source identity or content changed during recovery"
                    result.budget_events.extend(_coalesce_budget_events(goal_budget_events))
                    break

                for artifact in outcome.artifacts:
                    artifact.meta.setdefault("plan_id", chosen_plan.plan_id)
                    artifact.meta.setdefault("strategy_id", chosen_plan.strategy_id)
                    artifact.meta.setdefault("source_sha256", analysis.record.sha256)
                    artifact.meta.setdefault("source_slices", [asdict(item) for item in chosen_plan.slices])
                outcome.decode.telemetry.setdefault("goal", goal.value)
                outcome.decode.telemetry.setdefault("plan_id", chosen_plan.plan_id)
                outcome.decode.telemetry.setdefault("handler_id", chosen_handler.handler_id)
                result.goals.append(GoalExecution(goal.value, chosen_handler.handler_id, chosen_plan, outcome))
            except CancelledError as exc:
                failure = self._failure_outcome(f"cancelled:{exc}", OutcomeGrade.CANCELLED.value)
                if goal_root is not None and chosen_context is not None:
                    self._capture_artifacts(goal_root, before, failure, goal.value, chosen_context.budget)
                result.goals.append(
                    GoalExecution(goal.value, chosen_handler.handler_id if chosen_handler else "none", chosen_plan, failure)
                )
                result.error_code = "cancelled"
                result.error_detail = str(exc)
                result.budget_events.extend(_coalesce_budget_events(goal_budget_events))
                break
            except BudgetExceeded as exc:
                failure = self._failure_outcome(str(exc), OutcomeGrade.BUDGET_EXCEEDED.value)
                if goal_root is not None and chosen_context is not None:
                    self._capture_artifacts(goal_root, before, failure, goal.value, chosen_context.budget)
                result.goals.append(
                    GoalExecution(goal.value, chosen_handler.handler_id if chosen_handler else "none", chosen_plan, failure)
                )
            except SourceChangedError as exc:
                failure = self._failure_outcome(str(exc))
                if goal_root is not None and chosen_context is not None:
                    self._capture_artifacts(goal_root, before, failure, goal.value, chosen_context.budget)
                    for artifact in failure.artifacts:
                        artifact.validation_state = "source_changed"
                        artifact.fidelity_grade = OutcomeGrade.FAILED.value
                result.goals.append(
                    GoalExecution(goal.value, chosen_handler.handler_id if chosen_handler else "none", chosen_plan, failure)
                )
                result.error_code = "source_changed"
                result.error_detail = str(exc)
                for artifact in result.artifacts:
                    artifact.validation_state = "source_changed"
                    artifact.fidelity_grade = OutcomeGrade.FAILED.value
                result.budget_events.extend(_coalesce_budget_events(goal_budget_events))
                break
            except (CollisionError, ValidationError) as exc:
                failure = self._failure_outcome(f"publication_failed:{exc}")
                if goal_root is not None and chosen_context is not None:
                    self._capture_artifacts(goal_root, before, failure, goal.value, chosen_context.budget)
                result.goals.append(
                    GoalExecution(goal.value, chosen_handler.handler_id if chosen_handler else "none", chosen_plan, failure)
                )
            except (PathLayoutError, UnsafeSourceError) as exc:
                failure = self._failure_outcome(f"unsafe_path:{exc}")
                if goal_root is not None and chosen_context is not None:
                    self._capture_artifacts(goal_root, before, failure, goal.value, chosen_context.budget)
                result.goals.append(
                    GoalExecution(goal.value, chosen_handler.handler_id if chosen_handler else "none", chosen_plan, failure)
                )
            except Exception as exc:
                failure = self._failure_outcome(f"handler_failed:{exc.__class__.__name__}:{exc}")
                if goal_root is not None and chosen_context is not None:
                    self._capture_artifacts(goal_root, before, failure, goal.value, chosen_context.budget)
                result.goals.append(
                    GoalExecution(goal.value, chosen_handler.handler_id if chosen_handler else "none", chosen_plan, failure)
                )
            result.budget_events.extend(_coalesce_budget_events(goal_budget_events))
        return result

    def process_paths(
        self,
        input_root: Path,
        *,
        output_root: Path,
        recursive: bool,
        all_files: bool,
        goals: Iterable[RecoveryGoal | str],
        limits: ResourceLimits | None = None,
        cancellation: CancellationToken | None = None,
        complete_limit: int | None = None,
        save_raw_candidates: bool = False,
    ) -> Iterator[FileExecution]:
        limits = limits or self.limits
        cancellation = cancellation or CancellationToken()
        paths = list(iter_input_files(input_root, recursive=recursive, all_files=all_files))
        if complete_limit is not None:
            if complete_limit <= 0:
                raise ValueError("complete_limit must be greater than zero")
            paths = paths[:complete_limit]
        operation = partial(
            self.process_path,
            Path(input_root).resolve(strict=True),
            output_root=Path(output_root),
            goals=tuple(goals),
            limits=limits,
            cancellation=cancellation,
            save_raw_candidates=save_raw_candidates,
        )
        if limits.max_workers == 1 or len(paths) <= 1:
            for path in paths:
                yield operation(path)
            return
        with ThreadPoolExecutor(max_workers=limits.max_workers, thread_name_prefix="uncorrupter-recover") as executor:
            yield from executor.map(operation, paths)

    def persist_analysis(self, conn, run_id: int, analysis: FileAnalysis) -> int | None:
        if analysis.record is None:
            return None
        file_id = insert_file(conn, run_id, analysis.record, analysis.classification)
        if analysis.classification is None:
            transition_file(conn, file_id, "scanned")
        for event in analysis.budget_events:
            insert_budget_event(
                conn,
                run_id,
                file_id=file_id,
                scope=str(event.get("scope") or "file"),
                name=str(event.get("name") or "unknown"),
                limit_value=float(event.get("limit") or 0),
                consumed=float(event.get("consumed") or 0),
                outcome=str(event.get("outcome") or "unknown"),
            )
        return file_id

    def persist_execution(self, conn, run_id: int, execution: FileExecution) -> int | None:
        if execution.record is None:
            return None
        file_id = insert_file(conn, run_id, execution.record, execution.classification)
        transition_file(conn, file_id, "processing")
        for event in execution.budget_events:
            insert_budget_event(
                conn,
                run_id,
                file_id=file_id,
                scope=str(event.get("scope") or "file"),
                name=str(event.get("name") or "unknown"),
                limit_value=float(event.get("limit") or 0),
                consumed=float(event.get("consumed") or 0),
                outcome=str(event.get("outcome") or "unknown"),
            )

        for goal_execution in execution.goals:
            outcome = goal_execution.outcome
            candidate_id = insert_candidate(conn, run_id, file_id, outcome.candidate) if outcome.candidate else None
            for item in outcome.attempts:
                if not isinstance(item, dict) or "decoder" not in item or "ok" not in item:
                    continue
                attempted_candidate = item.get("candidate")
                attempted_candidate_id = (
                    insert_candidate(conn, run_id, file_id, attempted_candidate)
                    if isinstance(attempted_candidate, Candidate)
                    else None
                )
                attempted_decode = DecodeResult(
                    ok=bool(item.get("ok")),
                    decoder=str(item.get("decoder") or goal_execution.handler_id),
                    width=int(item.get("width") or 0),
                    height=int(item.get("height") or 0),
                    mode=str(item.get("mode") or ""),
                    decoded_format=str(item.get("decoded_format") or ""),
                    duration_ms=int(item.get("duration_ms") or 0),
                    frame_count=int(item.get("frame_count") or 0),
                    score=float(item.get("score") or 0.0),
                    error=str(item.get("error") or ""),
                    telemetry=dict(item.get("telemetry") or {}),
                )
                insert_attempt(
                    conn,
                    run_id,
                    file_id,
                    attempted_candidate_id,
                    attempted_decode,
                    phase=str(item.get("phase") or "candidate_attempt"),
                )
            telemetry = dict(outcome.decode.telemetry)
            telemetry.update(
                {
                    "goal": goal_execution.goal,
                    "handler_id": goal_execution.handler_id,
                    "plan": self._plan_evidence(goal_execution.plan),
                    "diagnostics": outcome.diagnostics,
                }
            )
            decode = replace(outcome.decode, telemetry=telemetry)
            attempt_id = insert_attempt(
                conn,
                run_id,
                file_id,
                candidate_id,
                decode,
                phase=f"goal:{goal_execution.goal}",
                outcome_grade=outcome.grade,
            )
            output_ids: list[int] = []
            artifact_output_ids: list[tuple[Artifact, int]] = []
            if outcome.artifacts:
                for artifact in outcome.artifacts:
                    output_id = insert_output(conn, run_id, file_id, attempt_id, outcome.candidate, decode, artifact, None)
                    output_ids.append(output_id)
                    artifact_output_ids.append((artifact, output_id))
                    insert_artifact_relation(
                        conn,
                        run_id,
                        child_output_id=output_id,
                        relation_type="derived_from",
                        parent_kind="source",
                        parent_identifier=f"sha256:{execution.record.sha256}",
                        locator={"slices": [asdict(item) for item in goal_execution.plan.slices]} if goal_execution.plan else {},
                        transform={
                            "goal": goal_execution.goal,
                            "handler_id": goal_execution.handler_id,
                            "plan_id": goal_execution.plan.plan_id if goal_execution.plan else None,
                        },
                    )
            else:
                output_ids.append(insert_output(conn, run_id, file_id, attempt_id, outcome.candidate, decode, None, None))

            primary_output_id = output_ids[0] if output_ids else None
            spans = telemetry.get("spans")
            if primary_output_id is not None and isinstance(spans, list):
                span_output_id = next(
                    (
                        output_id
                        for artifact, output_id in artifact_output_ids
                        if artifact.media_type.startswith("text/") and artifact.artifact_type != "diagnostics"
                    ),
                    primary_output_id,
                )
                insert_text_spans(conn, span_output_id, [item for item in spans if isinstance(item, dict)])
            members = telemetry.get("members")
            if isinstance(members, list):
                insert_archive_members(conn, run_id, file_id, [item for item in members if isinstance(item, dict)], output_id=primary_output_id)
            if execution.inspection is not None and execution.inspection.family == "package_document":
                insert_document_parts(conn, run_id, file_id, execution.inspection.parts, output_id=primary_output_id)
            streams = telemetry.get("streams")
            if isinstance(streams, list):
                insert_media_streams(conn, run_id, file_id, [item for item in streams if isinstance(item, dict)], output_id=primary_output_id)
            tool = telemetry.get("tool")
            if isinstance(tool, dict) and tool:
                tool_name = str(tool.get("name") or ({"pdf-native-v1": "qpdf", "media-native-v1": "ffmpeg", "external-adapter-v1": "external-archive-tool"}.get(goal_execution.handler_id, goal_execution.handler_id)))
                insert_tool_record(conn, run_id, tool_name, tool, file_id=file_id, attempt_id=attempt_id)

        status = execution.status
        error_code = execution.error_code
        error_detail = execution.error_detail
        if status in {"failed", "unavailable", "budget_exceeded", "cancelled"} and not error_detail:
            failures = [item.outcome.decode.error for item in execution.goals if item.outcome.decode.error]
            error_detail = "; ".join(failures) or status
        if status == "unavailable" and not error_code:
            error_code = "dependency_unavailable"
        elif status == "budget_exceeded" and not error_code:
            error_code = "budget_exceeded"
        elif status == "cancelled" and not error_code:
            error_code = "cancelled"
        elif status == "failed" and not error_code:
            error_code = "recovery_failed"
        transition_file(conn, file_id, status, error_code=error_code, error_detail=error_detail)
        return file_id
