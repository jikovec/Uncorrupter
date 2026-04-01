from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .classification import classify_record
from .db import insert_attempt, insert_file, insert_output
from .decoders import ffmpeg_available, probe_with_ffmpeg, probe_with_pillow, save_with_ffmpeg, save_with_pillow
from .engines import build_registry
from .intake import build_file_record, iter_input_files, read_bytes
from .scoring import score_candidate
from .types import Candidate, Classification, DecodeResult, FileRecord, RecoveryOutcome


def _output_kind(record: FileRecord, classification: Classification) -> str:
    if record.declared_kind:
        return record.declared_kind
    if record.byte0_kind != "unknown":
        return record.byte0_kind
    if classification.family != "unknown":
        return classification.family
    return "png"


class RecoveryPipeline:
    def __init__(self, engine_name: str = "jpeg-v1") -> None:
        registry = build_registry()
        if engine_name not in registry:
            raise ValueError(f"Unknown engine: {engine_name}")
        self.engine = registry[engine_name]

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
        attempts: list[dict[str, object]] = []

        for candidate in candidates:
            pillow_probe = probe_with_pillow(candidate.data)
            pillow_probe.score = score_candidate(candidate, pillow_probe, classification)
            attempts.append(
                {
                    "strategy_id": candidate.strategy_id,
                    "family": candidate.family,
                    "priority": candidate.priority,
                    "meta": candidate.meta,
                    "decoder": pillow_probe.decoder,
                    "ok": pillow_probe.ok,
                    "width": pillow_probe.width,
                    "height": pillow_probe.height,
                    "mode": pillow_probe.mode,
                    "decoded_format": pillow_probe.decoded_format,
                    "score": pillow_probe.score,
                    "error": pillow_probe.error,
                }
            )
            if pillow_probe.ok and (best_probe is None or pillow_probe.score > best_probe.score):
                best_candidate = candidate
                best_probe = pillow_probe

        if ffmpeg_available() and best_candidate is None:
            for candidate in candidates[:6]:
                ffmpeg_probe = probe_with_ffmpeg(candidate.data, candidate.family)
                ffmpeg_probe.score = score_candidate(candidate, ffmpeg_probe, classification)
                attempts.append(
                    {
                        "strategy_id": candidate.strategy_id,
                        "family": candidate.family,
                        "priority": candidate.priority,
                        "meta": candidate.meta,
                        "decoder": ffmpeg_probe.decoder,
                        "ok": ffmpeg_probe.ok,
                        "width": ffmpeg_probe.width,
                        "height": ffmpeg_probe.height,
                        "mode": ffmpeg_probe.mode,
                        "decoded_format": ffmpeg_probe.decoded_format,
                        "score": ffmpeg_probe.score,
                        "error": ffmpeg_probe.error,
                    }
                )
                if ffmpeg_probe.ok and (best_probe is None or ffmpeg_probe.score > best_probe.score):
                    best_candidate = candidate
                    best_probe = ffmpeg_probe

        if best_candidate is None or best_probe is None or not best_probe.ok:
            decode = DecodeResult(ok=False, decoder="none", error="no_candidate_succeeded")
            return RecoveryOutcome(candidate=None, decode=decode, attempts=attempts), None

        output_kind = _output_kind(record, classification)
        output_path = output_root / record.relative_path
        raw_candidate_path: Path | None = None

        final = save_with_pillow(best_candidate.data, output_path, output_kind)
        if not final.ok and ffmpeg_available():
            final = save_with_ffmpeg(best_candidate.data, best_candidate.family, output_path, output_kind)

        final.score = score_candidate(best_candidate, final, classification) if final.ok else float("-inf")

        if final.ok and save_raw_candidates:
            raw_candidate_path = output_root / "_raw_candidates" / record.relative_path
            raw_candidate_path.parent.mkdir(parents=True, exist_ok=True)
            raw_candidate_path = raw_candidate_path.with_suffix(raw_candidate_path.suffix + ".candidate")
            raw_candidate_path.write_bytes(best_candidate.data)

        return RecoveryOutcome(candidate=best_candidate, decode=final, attempts=attempts), raw_candidate_path

    def persist_scan(self, conn, run_id: int, classified: list[tuple[FileRecord, bytes, Classification]]) -> list[tuple[int, FileRecord, bytes, Classification]]:
        rows: list[tuple[int, FileRecord, bytes, Classification]] = []
        for record, data, classification in classified:
            file_id = insert_file(conn, run_id, record, classification)
            rows.append((file_id, record, data, classification))
        return rows

    def persist_recovery(self, conn, run_id: int, file_id: int, outcome: RecoveryOutcome, raw_candidate_path: Path | None) -> None:
        for attempt in outcome.attempts:
            candidate = Candidate(
                strategy_id=str(attempt["strategy_id"]),
                family=str(attempt["family"]),
                priority=int(attempt["priority"]),
                data=b"",
                meta=dict(attempt.get("meta") or {}),
            )
            decode = DecodeResult(
                ok=bool(attempt["ok"]),
                decoder=str(attempt["decoder"]),
                width=int(attempt.get("width") or 0),
                height=int(attempt.get("height") or 0),
                mode=str(attempt.get("mode") or ""),
                decoded_format=str(attempt.get("decoded_format") or ""),
                score=float(attempt["score"]),
                error=str(attempt["error"] or ""),
            )
            insert_attempt(conn, run_id, file_id, candidate, decode)
        insert_output(conn, run_id, file_id, outcome.candidate, outcome.decode, raw_candidate_path)
