from __future__ import annotations

from dataclasses import replace

from ..atomic import AtomicArtifactWriter
from ..decoders import probe_with_pillow, save_with_pillow, sha256_path
from ..engines.registry import build_registry as build_engine_registry
from ..scoring import score_candidate
from ..types import Artifact, CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome, SourceSliceSpec
from .base import (
    CapabilityRecord,
    FormatHandler,
    HandlerContext,
    InspectionResult,
    RecoveryGoal,
)


_IMAGE_FAMILIES = ("jpeg", "png", "gif", "bmp", "tiff", "webp", "heif", "avif", "jp2", "raw")
_VIDEO_FAMILIES = ("mp4", "mov", "avi", "mkv", "webm", "mpegts", "mpegps", "flv", "asf", "wmv")


class LegacyMediaHandler(FormatHandler):
    handler_id = "legacy-media-v2"

    def __init__(self) -> None:
        self._engine = build_engine_registry()["baseline-v2"]

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        records: list[CapabilityRecord] = []
        for family in ("jpeg",):
            is_jpeg = family == "jpeg"
            records.append(
                CapabilityRecord(
                    family=family,
                    variants=(family,),
                    extensions=(".jpg", ".jpeg", ".jpe"),
                    signatures=(f"builtin:{family}",),
                    operations={
                        "detect": "validated",
                        "inspect": "baseline",
                        "validate": "baseline",
                        "repair": "validated" if is_jpeg else "baseline",
                        "normalize": "baseline",
                        "extract": "none",
                        "preview": "baseline",
                        "carve": "partial",
                    },
                    tools={"required": (), "optional": ("ffmpeg", "ffprobe") if family in _VIDEO_FAMILIES else ()},
                    limits={"max_candidate_bytes": 256 * (1 << 20), "max_candidates": 64},
                    encryption="not_applicable",
                    active_content="never_executed",
                    outputs=({"kind": "repaired", "media_type": f"image/{family}" if family in _IMAGE_FAMILIES else f"video/{family}"},),
                    fidelity="JPEG repair candidates are independently decoded before selection; re-encoded normalize and preview artifacts are labeled as derivatives.",
                    fixtures=("legacy-valid", "legacy-truncated") if is_jpeg else ("legacy-valid",),
                    availability="available" if is_jpeg or family in {"png", "gif", "bmp", "tiff", "webp"} else "partial",
                    handler_id=self.handler_id,
                )
            )
        return tuple(records)

    def inspect(self, context: HandlerContext) -> InspectionResult:
        context.cancellation.checkpoint()
        return InspectionResult(
            family=context.classification.family,
            valid=context.classification.confidence >= 0.5,
            confidence=context.classification.confidence,
            diagnostics=[{"classification": context.classification.label, "evidence": context.classification.evidence}],
        )

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        if goal not in {RecoveryGoal.REPAIR, RecoveryGoal.NORMALIZE, RecoveryGoal.PREVIEW, RecoveryGoal.CARVE}:
            return []
        return [
            CandidatePlan(
                plan_id=f"{self.handler_id}:legacy-eager",
                handler_id=self.handler_id,
                strategy_id="legacy-eager",
                family=context.classification.family,
                goal=goal.value,
                priority=100,
                slices=(SourceSliceSpec(0, context.source.size),),
                estimated_materialized_bytes=context.source.size,
                estimated_output_bytes=context.source.size,
                provenance=({"kind": "whole_file"},),
            )
        ]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        context.cancellation.checkpoint()
        data = plan.materialize(context.source, max_bytes=context.limits.max_candidate_bytes)
        generated = self._engine.generate_candidates(context.record, data, context.classification)
        source_hash = context.record.sha256
        remaining_candidates = int(context.budget.remaining("candidates"))
        remaining_bytes = int(context.budget.remaining("candidate_bytes"))
        candidates = []
        selected_extra_bytes = 0
        for candidate in generated:
            if len(candidates) >= remaining_candidates:
                break
            extra_bytes = 0 if candidate.data_sha256 == source_hash else len(candidate.data)
            if selected_extra_bytes + extra_bytes > remaining_bytes:
                continue
            candidates.append(candidate)
            selected_extra_bytes += extra_bytes
        context.budget.consume("candidates", len(candidates))
        context.budget.consume(
            "candidate_bytes",
            selected_extra_bytes,
        )
        truncated = len(candidates) < len(generated)

        attempts: list[dict[str, object]] = []
        cache: dict[str, DecodeResult] = {}
        best_candidate = None
        best_probe = None
        for candidate in candidates:
            context.cancellation.checkpoint()
            if candidate.dedupe_hash not in cache:
                cache[candidate.dedupe_hash] = probe_with_pillow(candidate.data)
            probe = replace(cache[candidate.dedupe_hash])
            probe.score = score_candidate(candidate, probe, context.classification)
            attempts.append(
                {
                    "candidate": candidate,
                    "decoder": probe.decoder,
                    "phase": "image_probe",
                    "ok": probe.ok,
                    "width": probe.width,
                    "height": probe.height,
                    "mode": probe.mode,
                    "decoded_format": probe.decoded_format,
                    "frame_count": probe.frame_count,
                    "score": probe.score,
                    "error": probe.error,
                    "telemetry": probe.telemetry,
                }
            )
            if probe.ok and (best_probe is None or probe.score > best_probe.score):
                best_candidate = candidate
                best_probe = probe

        if best_candidate is None or best_probe is None:
            return RecoveryOutcome(
                candidate=None,
                decode=DecodeResult(
                    ok=False,
                    decoder="pillow",
                    error="no_candidate_succeeded",
                    telemetry={"candidate_count": len(candidates), "generated_candidate_count": len(generated), "candidate_budget_truncated": truncated},
                ),
                attempts=attempts,
                grade=OutcomeGrade.FAILED.value,
            )

        if context.output_root is None:
            best_probe.telemetry.update({"candidate_count": len(candidates), "generated_candidate_count": len(generated), "candidate_budget_truncated": truncated, "publication": "not_requested"})
            return RecoveryOutcome(
                candidate=best_candidate,
                decode=best_probe,
                attempts=attempts,
                grade=OutcomeGrade.PREVIEW_ONLY.value,
            )

        output_name = {
            RecoveryGoal.REPAIR.value: "repaired.jpg",
            RecoveryGoal.NORMALIZE.value: "normalized.jpg",
            RecoveryGoal.PREVIEW.value: "preview.jpg",
            RecoveryGoal.CARVE.value: "carved.jpg",
        }[plan.goal]
        if plan.goal == RecoveryGoal.CARVE.value:
            published = AtomicArtifactWriter(context.output_root, budget=context.budget).publish_bytes(
                output_name,
                best_candidate.data,
                validator=lambda path: probe_with_pillow(path.read_bytes()).ok,
            )
            final = replace(best_probe, output_path=published.path)
        else:
            final = save_with_pillow(
                best_candidate.data,
                context.output_root / output_name,
                "jpeg",
                budget=context.budget,
            )
        final.score = score_candidate(best_candidate, final, context.classification) if final.ok else float("-inf")
        final.telemetry.update({"candidate_count": len(candidates), "generated_candidate_count": len(generated), "candidate_budget_truncated": truncated, "selected_content_hash": best_candidate.dedupe_hash})
        attempts.append(
            {
                "candidate": best_candidate,
                "decoder": final.decoder,
                "phase": f"{plan.goal}_final",
                "ok": final.ok,
                "width": final.width,
                "height": final.height,
                "mode": final.mode,
                "decoded_format": final.decoded_format,
                "frame_count": final.frame_count,
                "score": final.score,
                "error": final.error,
                "telemetry": final.telemetry,
            }
        )
        artifacts: list[Artifact] = []
        if final.ok and final.output_path is not None:
            artifact_type = "preview" if plan.goal == RecoveryGoal.PREVIEW.value else "raw_fragment" if plan.goal == RecoveryGoal.CARVE.value else "normalized" if plan.goal == RecoveryGoal.NORMALIZE.value else "repaired"
            artifacts.append(
                Artifact(
                    artifact_type=artifact_type,
                    path=final.output_path,
                    sha256=sha256_path(final.output_path),
                    decoder=final.decoder,
                    width=final.width,
                    height=final.height,
                    frame_count=final.frame_count,
                    size=final.output_path.stat().st_size,
                    media_type="image/jpeg",
                    fidelity_grade=OutcomeGrade.PREVIEW_ONLY.value if plan.goal == RecoveryGoal.PREVIEW.value else OutcomeGrade.PARTIAL_CONTENT.value if plan.goal == RecoveryGoal.CARVE.value else OutcomeGrade.VALIDATED_NORMALIZED.value,
                    validation_state="decoder_validated",
                    validators=[{"name": "pillow", "ok": True}],
                    published=True,
                )
            )
        grade = (
            OutcomeGrade.PREVIEW_ONLY.value
            if final.ok and plan.goal == RecoveryGoal.PREVIEW.value
            else OutcomeGrade.PARTIAL_CONTENT.value
            if final.ok and plan.goal == RecoveryGoal.CARVE.value
            else OutcomeGrade.VALIDATED_NORMALIZED.value
            if final.ok
            else OutcomeGrade.FAILED.value
        )
        return RecoveryOutcome(
            candidate=best_candidate,
            decode=final,
            attempts=attempts,
            artifacts=artifacts,
            grade=grade,
        )
