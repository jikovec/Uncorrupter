from __future__ import annotations

from .constants import (
    ALL_KINDS,
    ASF_HEADER_GUID,
    AVI,
    BMP_SIG,
    EBML_HEADER,
    FLV_SIG,
    GIF87A,
    GIF89A,
    ISOBMFF_BRANDS_TO_KIND,
    JP2_SIG,
    MPEG_PS_PACK,
    PNG_SIG,
    RIFF,
    SOI,
    TIFF_BE,
    TIFF_LE,
    WEBP,
)
from .types import SignatureHit


def find_all(data: bytes, needle: bytes, limit: int | None = None) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        if limit is not None and len(positions) >= limit:
            break
        start = idx + 1
    return positions


def sample_positions(positions: list[int], limit: int) -> list[int]:
    if len(positions) <= limit:
        return positions[:]
    result: list[int] = []
    used: set[int] = set()
    anchors = [0, 1, 2, len(positions) - 3, len(positions) - 2, len(positions) - 1]
    for idx in anchors:
        if 0 <= idx < len(positions):
            value = positions[idx]
            if value not in used:
                used.add(value)
                result.append(value)
    remaining = limit - len(result)
    if remaining <= 0:
        return sorted(result)
    step = (len(positions) - 1) / max(1, remaining)
    for i in range(remaining):
        idx = round(i * step)
        value = positions[idx]
        if value not in used:
            used.add(value)
            result.append(value)
    return sorted(result)


def _riff_hits(data: bytes, limit_per_type: int) -> list[SignatureHit]:
    hits: list[SignatureHit] = []
    positions = sample_positions(find_all(data, RIFF), limit_per_type)
    for pos in positions:
        if pos + 12 > len(data):
            continue
        brand = data[pos + 8:pos + 12]
        if brand == WEBP:
            hits.append(SignatureHit(family="webp", signature_type="riff_webp", offset=pos, confidence=0.99 if pos == 0 else 0.9))
        elif brand == AVI:
            hits.append(SignatureHit(family="avi", signature_type="riff_avi", offset=pos, confidence=0.98 if pos == 0 else 0.9))
    return hits


def _isobmff_hits(data: bytes, limit_per_type: int) -> list[SignatureHit]:
    hits: list[SignatureHit] = []
    positions = sample_positions(find_all(data, b"ftyp"), limit_per_type)
    for pos in positions:
        if pos < 4 or pos + 8 > len(data):
            continue
        start = pos - 4
        brand = data[pos + 4:pos + 8]
        family = ISOBMFF_BRANDS_TO_KIND.get(brand, "mp4")
        signature_type = f"ftyp:{brand.decode('latin1', errors='replace').strip() or 'unknown'}"
        confidence = 0.99 if start == 0 else 0.9
        hits.append(SignatureHit(family=family, signature_type=signature_type, offset=start, confidence=confidence))
    return hits


def _ebml_hits(data: bytes, limit_per_type: int) -> list[SignatureHit]:
    hits: list[SignatureHit] = []
    positions = sample_positions(find_all(data, EBML_HEADER), limit_per_type)
    for pos in positions:
        window = data[pos:pos + 128].lower()
        family = "webm" if b"webm" in window else "mkv"
        hits.append(SignatureHit(family=family, signature_type="ebml", offset=pos, confidence=0.98 if pos == 0 else 0.9))
    return hits


def _mpegts_hits(data: bytes, limit_per_type: int) -> list[SignatureHit]:
    hits: list[SignatureHit] = []
    scan_len = min(len(data), 8192)
    best_offset = None
    best_score = 0
    for offset in range(min(188, scan_len)):
        score = 0
        pos = offset
        while pos < scan_len:
            if data[pos] == 0x47:
                score += 1
            pos += 188
        if score > best_score:
            best_score = score
            best_offset = offset
    if best_offset is not None and best_score >= 4:
        hits.append(
            SignatureHit(
                family="mpegts",
                signature_type="ts_sync",
                offset=best_offset,
                confidence=min(0.99, 0.6 + (best_score / 20.0)),
            )
        )
    return hits[:limit_per_type]


def scan_signatures(data: bytes, limit_per_type: int = 24) -> list[SignatureHit]:
    hits: list[SignatureHit] = []

    for pos in sample_positions(find_all(data, SOI), limit_per_type):
        hits.append(SignatureHit(family="jpeg", signature_type="jpeg_soi", offset=pos, confidence=0.99 if pos == 0 else 0.9))
    for pos in sample_positions(find_all(data, PNG_SIG), limit_per_type):
        hits.append(SignatureHit(family="png", signature_type="png_sig", offset=pos, confidence=0.99 if pos == 0 else 0.9))
    for pos in sample_positions(sorted(set(find_all(data, GIF87A) + find_all(data, GIF89A))), limit_per_type):
        hits.append(SignatureHit(family="gif", signature_type="gif_header", offset=pos, confidence=0.98 if pos == 0 else 0.88))
    for pos in sample_positions(find_all(data, BMP_SIG), limit_per_type):
        hits.append(SignatureHit(family="bmp", signature_type="bmp_header", offset=pos, confidence=0.95 if pos == 0 else 0.65))
    for pos in sample_positions(sorted(set(find_all(data, TIFF_LE) + find_all(data, TIFF_BE))), limit_per_type):
        hits.append(SignatureHit(family="tiff", signature_type="tiff_header", offset=pos, confidence=0.98 if pos == 0 else 0.88))
    for pos in sample_positions(find_all(data, FLV_SIG), limit_per_type):
        hits.append(SignatureHit(family="flv", signature_type="flv_header", offset=pos, confidence=0.98 if pos == 0 else 0.85))
    for pos in sample_positions(find_all(data, MPEG_PS_PACK), limit_per_type):
        hits.append(SignatureHit(family="mpegps", signature_type="mpegps_pack", offset=pos, confidence=0.98 if pos == 0 else 0.85))
    for pos in sample_positions(find_all(data, ASF_HEADER_GUID), limit_per_type):
        hits.append(SignatureHit(family="asf", signature_type="asf_guid", offset=pos, confidence=0.98 if pos == 0 else 0.85))
    for pos in sample_positions(find_all(data, JP2_SIG), limit_per_type):
        hits.append(SignatureHit(family="jp2", signature_type="jp2_sig", offset=pos, confidence=0.99 if pos == 0 else 0.9))

    hits.extend(_riff_hits(data, limit_per_type))
    hits.extend(_isobmff_hits(data, limit_per_type))
    hits.extend(_ebml_hits(data, limit_per_type))
    hits.extend(_mpegts_hits(data, limit_per_type))

    hits.sort(key=lambda item: (item.offset, -item.confidence, item.family, item.signature_type))
    return hits


def summarize_signature_hits(hits: list[SignatureHit]) -> dict[str, int]:
    summary = {kind: 0 for kind in ALL_KINDS}
    for hit in hits:
        summary[hit.family] = summary.get(hit.family, 0) + 1
    return {family: count for family, count in summary.items() if count > 0}


def detect_anywhere_kind(hits: list[SignatureHit]) -> str:
    if not hits:
        return "unknown"
    ranked = sorted(hits, key=lambda item: (-item.confidence, item.offset, item.family))
    return ranked[0].family


def header_kind_at_byte0(data: bytes) -> str:
    for hit in scan_signatures(data, limit_per_type=4):
        if hit.offset == 0:
            return hit.family
    return "unknown"
