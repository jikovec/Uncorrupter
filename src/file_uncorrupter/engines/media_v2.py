from __future__ import annotations

from ..constants import VIDEO_KINDS
from ..signature_index import find_all, sample_positions
from ..types import Candidate, Classification, FileRecord
from .base import RecoveryEngine
from .jpeg_v1 import JPEGRecoveryEngineV1


class BaselineRecoveryEngineV2(RecoveryEngine):
    name = "baseline-v2"
    families = (
        "jpeg", "png", "gif", "bmp", "tiff", "webp", "heif", "avif", "jp2", "raw",
        "mp4", "mov", "avi", "mkv", "webm", "mpegts", "mpegps", "flv", "asf", "wmv",
    )

    def __init__(self) -> None:
        self.jpeg = JPEGRecoveryEngineV1()

    def generate_candidates(self, record: FileRecord, data: bytes, classification: Classification) -> list[Candidate]:
        if classification.family == "jpeg":
            return self.jpeg.generate_candidates(record, data, classification)
        if classification.family in VIDEO_KINDS:
            return self._video_candidates(record, data, classification)
        return self._generic_blob_candidates(record, data, classification)

    def _generic_blob_candidates(self, record: FileRecord, data: bytes, classification: Classification) -> list[Candidate]:
        candidates: list[Candidate] = []
        seen: set[str] = set()

        def add(strategy_id: str, payload: bytes, priority: int, *, offset: int | None = None) -> None:
            candidate = Candidate(
                strategy_id=strategy_id,
                family=classification.family,
                priority=priority,
                data=payload,
                candidate_kind="slice",
                provenance=[{"kind": "slice", "offset": offset}],
                meta={"offset": offset},
            )
            if candidate.strategy_hash in seen:
                return
            seen.add(candidate.strategy_hash)
            candidates.append(candidate)

        add("full_file", data, 100, offset=0)
        relevant = [hit.offset for hit in record.signature_hits if hit.family == classification.family]
        for offset in sample_positions(sorted(set(relevant)), 8):
            add("signature_offset_to_end", data[offset:], 96 if offset > 0 else 99, offset=offset)
        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.strategy_id))
        return candidates

    def _video_candidates(self, record: FileRecord, data: bytes, classification: Classification) -> list[Candidate]:
        candidates: list[Candidate] = []
        seen: set[str] = set()

        def add(strategy_id: str, payload: bytes, priority: int, *, offset: int) -> None:
            candidate = Candidate(
                strategy_id=strategy_id,
                family=classification.family,
                priority=priority,
                data=payload,
                candidate_kind="container_rebuild_plan" if offset > 0 else "slice",
                provenance=[{"kind": "slice", "offset": offset}],
                meta={"offset": offset},
            )
            if candidate.strategy_hash in seen:
                return
            seen.add(candidate.strategy_hash)
            candidates.append(candidate)

        add("full_file", data, 100, offset=0)
        relevant_hits = [hit.offset for hit in record.signature_hits if hit.family == classification.family]
        for offset in sample_positions(sorted(set(relevant_hits)), 8):
            add("signature_offset_to_end", data[offset:], 99 if offset > 0 else 100, offset=offset)

        if classification.family == "mpegts":
            for offset in sample_positions(find_all(data[:8192], b"\x47"), 8):
                if offset < len(data):
                    add("ts_sync_offset_to_end", data[offset:], 101 if offset > 0 else 100, offset=offset)

        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.strategy_id))
        return candidates
