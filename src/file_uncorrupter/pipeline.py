from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .classification import classify_record
from .constants import VIDEO_KINDS
from .db import insert_attempt, insert_candidate, insert_file, insert_output
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
from .intake import build_file_record, iter_input_files, read_bytes
from .scoring import score_candidate
from .types import Artifact, Candidate, Classification, DecodeResult, FileRecord, RecoveryOutcome


def _image_output_kind(record: FileRecord, classification: Classification) -> str:
    if record.declared_kind and record.declared_kind not in VIDEO_KINDS:
        return record.declared_kind
    if record.byte0_kind != "unknown" and record.byte0_kind not in VIDEO_KINDS:
        return record.byte0_kind
    if classification.family != "unknown" and classification.family not in VIDEO_KINDS:
        return classification.family
    return "png"


class RecoveryPipeline:
    def __init__(self, engine_name: str = "baseline-v2", *, max_ffmpeg_candidates: int = 12) -> None:
        registry = build_registry()
        if engine_name not in registry:
            raise ValueError(f"Unknown engine: {engine_name}")
        self.engine = registry[engine_name]
        self.max_ffmpeg_candidates = max_ffmpeg_candidates

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
        if classification.family not in self.engine.families:
            decode = DecodeResult(ok=False, decoder="none", error=f"no_engine_for_family:{classification.family}")
            return RecoveryOutcome(candidate=None, decode=decode, attempts=[]), None

        candidates = self.engine.generate_candidates(record, data, classification)
        best_candidate: Candidate | None = None
        best_probe: DecodeResult | None = None
        best_attempt_phase = "probe"
        attempts: list[dict[str, object]] = []

        for candidate in candidates:
            if classification.family in VIDEO_KINDS:
                probe = probe_video_with_ffmpeg(candidate.data, candidate.family)
                phase = "video_probe"
            else:
                probe = probe_with_pillow(candidate.data)
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
                ffmpeg_probe = probe_with_ffmpeg(candidate.data, candidate.family)
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
            output_path = output_root / record.relative_path
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
                    )
                ]
        final.score = score_candidate(best_candidate, final, classification) if final.ok else float("-inf")

        if final.ok and save_raw_candidates:
            raw_candidate_path = output_root / "_raw_candidates" / record.relative_path
            raw_candidate_path.parent.mkdir(parents=True, exist_ok=True)
            raw_candidate_path = raw_candidate_path.with_suffix(raw_candidate_path.suffix + ".candidate")
            raw_candidate_path.write_bytes(best_candidate.data)

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
