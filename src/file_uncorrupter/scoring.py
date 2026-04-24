from __future__ import annotations

from .types import Candidate, Classification, DecodeResult


VIDEO_FAMILIES = {"mp4", "mov", "avi", "mkv", "webm", "mpegts", "mpegps", "flv", "asf", "wmv"}


def score_candidate(candidate: Candidate, decode: DecodeResult, classification: Classification) -> float:
    if not decode.ok:
        return float("-inf")

    if classification.family in VIDEO_FAMILIES:
        score = 0.0
        score += candidate.priority * 2.0
        score += min(decode.width * decode.height, 50_000_000) / 5000.0
        score += min(decode.duration_ms / 1000.0, 600.0)
        score += min(decode.frame_count, 300) * 2.0
        if classification.family == candidate.family:
            score += 80.0
        if candidate.candidate_kind == "container_rebuild_plan":
            score += 35.0
        if "signature_offset" in candidate.strategy_id and classification.label.endswith("away_from_byte0"):
            score += 45.0
        if classification.label == "mpegts_desync_or_partial_packets" and "ts_sync" in candidate.strategy_id:
            score += 50.0
        return score

    score = 0.0
    score += min(decode.area, 50_000_000) / 1000.0
    score += candidate.priority * 2.0
    score += decode.score * 20.0

    if classification.family == candidate.family:
        score += 80.0
    if classification.label == "jpeg_missing_dht" and "dht" in candidate.strategy_id:
        score += 50.0
    if classification.label == "jpeg_missing_soi_internal_structure" and ("synthetic_soi" in candidate.strategy_id or "rebuild_header" in candidate.strategy_id):
        score += 65.0
    if classification.label == "jpeg_missing_eoi" and "append_eoi" in candidate.strategy_id:
        score += 40.0
    if "restart_window" in candidate.strategy_id:
        score += 30.0
    if decode.width < 8 or decode.height < 8:
        score -= 300.0
    if decode.width > 30000 or decode.height > 30000:
        score -= 200.0
    return score
