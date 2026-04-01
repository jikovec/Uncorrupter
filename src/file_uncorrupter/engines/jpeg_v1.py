from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image

from ..classification import find_all, jpeg_marker_stats
from ..constants import APP0, APP1, DHT, DQT, EOI, JPEG_SOF_MARKERS, SOI, SOS
from ..types import Candidate, Classification, FileRecord
from .base import RecoveryEngine


def _sample_positions(positions: list[int], limit: int) -> list[int]:
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


def _extract_jpeg_segments(data: bytes, marker: bytes) -> list[bytes]:
    segments: list[bytes] = []
    i = 2 if data.startswith(SOI) else 0
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        if i + 1 >= len(data):
            break
        current = data[i:i + 2]
        if current == SOS:
            break
        if current in (SOI, EOI) or (0xD0 <= data[i + 1] <= 0xD7):
            i += 2
            continue
        if i + 4 > len(data):
            break
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if length < 2:
            break
        end = i + 2 + length
        if end > len(data):
            break
        if current == marker:
            segments.append(data[i:end])
        i = end
    return segments


@lru_cache(maxsize=1)
def standard_dht_segments() -> bytes:
    img = Image.new("L", (8, 8), 128)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    sample = buffer.getvalue()
    segments = _extract_jpeg_segments(sample, DHT)
    if not segments:
        return b""
    return b"".join(segments)


class JPEGRecoveryEngineV1(RecoveryEngine):
    name = "jpeg-v1"
    families = ("jpeg",)

    def generate_candidates(self, record: FileRecord, data: bytes, classification: Classification) -> list[Candidate]:
        stats = jpeg_marker_stats(data)
        candidates: list[Candidate] = []
        seen: set[tuple[str, bytes]] = set()

        def add(strategy_id: str, payload: bytes, priority: int, **meta: object) -> None:
            key = (strategy_id, payload)
            if key in seen:
                return
            seen.add(key)
            candidates.append(Candidate(strategy_id=strategy_id, family="jpeg", priority=priority, data=payload, meta=meta))

        add("full_file", data, 100)
        add("prepend_soi_full", SOI + data, 98)
        add("append_eoi_full", data + EOI, 97)
        add("prepend_soi_append_eoi_full", SOI + data + EOI, 96)

        soi_positions = _sample_positions(find_all(data, SOI), 12)
        eoi_positions = find_all(data, EOI)
        sos_positions = _sample_positions(find_all(data, SOS), 12)
        marker_positions: list[int] = []
        for marker in [APP0, APP1, DQT, DHT, *JPEG_SOF_MARKERS, SOS]:
            marker_positions.extend(find_all(data, marker))
        marker_positions = _sample_positions(sorted(set(marker_positions)), 20)

        for soi in soi_positions:
            later_eois = [e for e in eoi_positions if e > soi]
            for eoi in _sample_positions(later_eois, 5):
                add("soi_to_sampled_eoi", data[soi:eoi + 2], 95, start=soi, end=eoi + 2)
            add("soi_to_end", data[soi:], 94, start=soi)
            add("soi_to_end_append_eoi", data[soi:] + EOI, 93, start=soi)
            for tail_len in (65536, 262144, 1048576):
                end = min(len(data), soi + tail_len)
                if end - soi >= 128:
                    add(f"soi_tail_{tail_len}", data[soi:end], 92, start=soi, end=end)
                    add(f"soi_tail_{tail_len}_append_eoi", data[soi:end] + EOI, 91, start=soi, end=end)

        for pos in marker_positions:
            for back in (0, 128, 512, 2048, 8192, 32768):
                start = max(0, pos - back)
                add(f"synthetic_soi_back_{back}", SOI + data[start:], 88, start=start)
                add(f"synthetic_soi_back_{back}_append_eoi", SOI + data[start:] + EOI, 87, start=start)
                later_eois = [e for e in eoi_positions if e > pos]
                for eoi in _sample_positions(later_eois, 3):
                    add(f"synthetic_soi_back_{back}_to_eoi", SOI + data[start:eoi + 2], 86, start=start, end=eoi + 2)

        dht_blob = standard_dht_segments()
        if dht_blob and stats["sos_count"] > 0 and stats["dht_count"] == 0:
            for sos in sos_positions:
                repaired = data[:sos] + dht_blob + data[sos:]
                add("inject_standard_dht_before_sos", repaired, 99, sos=sos)
                add("inject_standard_dht_before_sos_append_eoi", repaired + EOI, 98, sos=sos)
                add("prepend_soi_inject_standard_dht_before_sos", SOI + repaired, 97, sos=sos)
                add("prepend_soi_inject_standard_dht_before_sos_append_eoi", SOI + repaired + EOI, 96, sos=sos)
                for back in (128, 512, 2048, 8192):
                    start = max(0, sos - back)
                    windowed = data[start:sos] + dht_blob + data[sos:]
                    add(f"windowed_inject_standard_dht_back_{back}", SOI + windowed, 95, start=start, sos=sos)
                    add(f"windowed_inject_standard_dht_back_{back}_append_eoi", SOI + windowed + EOI, 94, start=start, sos=sos)

        if classification.label == "jpeg_missing_eoi":
            add("classification_hint_append_eoi", data + EOI, 105)
        elif classification.label == "jpeg_missing_soi_internal_structure":
            for pos in marker_positions[:8]:
                start = max(0, pos - 2048)
                add("classification_hint_synthetic_soi", SOI + data[start:], 104, start=start)
        elif classification.label == "jpeg_missing_dht" and dht_blob and sos_positions:
            sos = sos_positions[0]
            add("classification_hint_inject_standard_dht", data[:sos] + dht_blob + data[sos:], 106, sos=sos)

        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.strategy_id))
        return candidates
