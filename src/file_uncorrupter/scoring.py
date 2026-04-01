from __future__ import annotations

from .types import Candidate, Classification, DecodeResult


def score_candidate(candidate: Candidate, decode: DecodeResult, classification: Classification) -> float:
    if not decode.ok:
        return float("-inf")

    score = 0.0
    score += min(decode.area, 50_000_000) / 1000.0
    score += candidate.priority * 2.0
    score += decode.score * 20.0

    if classification.family == candidate.family:
        score += 80.0
    if classification.label == "jpeg_missing_dht" and "dht" in candidate.strategy_id:
        score += 50.0
    if classification.label == "jpeg_missing_soi_internal_structure" and "synthetic_soi" in candidate.strategy_id:
        score += 40.0
    if classification.label == "jpeg_missing_eoi" and "append_eoi" in candidate.strategy_id:
        score += 40.0
    if decode.width < 8 or decode.height < 8:
        score -= 300.0
    if decode.width > 30000 or decode.height > 30000:
        score -= 200.0
    return score
