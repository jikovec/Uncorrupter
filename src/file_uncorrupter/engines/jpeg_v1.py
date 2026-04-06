from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image

from ..classification import jpeg_marker_stats
from ..constants import APP0, APP1, DHT, DQT, DRI, EOI, JPEG_SOF_MARKERS, SOI, SOS
from ..signature_index import find_all, sample_positions
from ..types import Candidate, Classification, FileRecord
from .base import RecoveryEngine


HEADER_MARKERS = {APP0, APP1, DQT, DHT, DRI, *JPEG_SOF_MARKERS}


def _extract_jpeg_segments(data: bytes, marker: bytes) -> list[bytes]:
    segments: list[bytes] = []
    i = 2 if data.startswith(SOI) else 0
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        current = data[i:i + 2]
        if current == SOS:
            break
        if current in (SOI, EOI) or (0xD0 <= data[i + 1] <= 0xD7):
            i += 2
            continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if length < 2:
            i += 1
            continue
        end = i + 2 + length
        if end > len(data):
            i += 1
            continue
        if current == marker:
            segments.append(data[i:end])
        i = end
    return segments


def _scan_complete_segments_anywhere(data: bytes, markers: set[bytes], limit_per_marker: int = 8) -> dict[bytes, list[tuple[int, bytes]]]:
    found: dict[bytes, list[tuple[int, bytes]]] = {marker: [] for marker in markers}
    i = 0
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i:i + 2]
        if marker not in markers:
            i += 1
            continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if length < 2:
            i += 1
            continue
        end = i + 2 + length
        if end > len(data):
            i += 1
            continue
        bucket = found[marker]
        if len(bucket) < limit_per_marker:
            bucket.append((i, data[i:end]))
        i = end
    return found


def _nearest_segment(segments: list[tuple[int, bytes]], target: int) -> bytes | None:
    if not segments:
        return None
    ranked = sorted(segments, key=lambda item: (abs(target - item[0]), item[0]))
    return ranked[0][1]


@lru_cache(maxsize=1)
def standard_dht_segments() -> bytes:
    img = Image.new("L", (8, 8), 128)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    sample = buffer.getvalue()
    segments = _extract_jpeg_segments(sample, DHT)
    return b"".join(segments)


@lru_cache(maxsize=1)
def standard_dqt_segments() -> bytes:
    img = Image.new("L", (8, 8), 128)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    sample = buffer.getvalue()
    segments = _extract_jpeg_segments(sample, DQT)
    return b"".join(segments)


def _extract_rebuild_segments(data: bytes, sos: int) -> tuple[bytes, bytes, bytes, bytes, bytes]:
    found = _scan_complete_segments_anywhere(data, HEADER_MARKERS)
    app_segments = []
    for marker in (APP0, APP1):
        segment = _nearest_segment(found.get(marker, []), sos)
        if segment is not None:
            app_segments.append(segment)
    dqt_segments = b"".join(segment for _, segment in found.get(DQT, [])[:4]) or standard_dqt_segments()
    dht_segments = b"".join(segment for _, segment in found.get(DHT, [])[:4]) or standard_dht_segments()
    dri_segment = _nearest_segment(found.get(DRI, []), sos) or b""

    sof_segment = b""
    for marker in JPEG_SOF_MARKERS:
        chosen = _nearest_segment(found.get(marker, []), sos)
        if chosen is not None:
            sof_segment = chosen
            break

    return b"".join(app_segments[:2]), dqt_segments, sof_segment, dht_segments, dri_segment


class JPEGRecoveryEngineV1(RecoveryEngine):
    name = "jpeg-v1"
    families = ("jpeg",)

    def generate_candidates(self, record: FileRecord, data: bytes, classification: Classification) -> list[Candidate]:
        stats = jpeg_marker_stats(data)
        candidates: list[Candidate] = []
        seen: set[str] = set()

        def add(strategy_id: str, payload: bytes, priority: int, *, candidate_kind: str = "slice", provenance: list[dict[str, object]] | None = None, **meta: object) -> None:
            candidate = Candidate(
                strategy_id=strategy_id,
                family="jpeg",
                priority=priority,
                data=payload,
                candidate_kind=candidate_kind,
                provenance=provenance or [],
                meta=meta,
            )
            if candidate.dedupe_hash in seen:
                return
            seen.add(candidate.dedupe_hash)
            candidates.append(candidate)

        add("full_file", data, 100, provenance=[{"kind": "whole_file"}])
        add("prepend_soi_full", SOI + data, 98, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}])
        add("append_eoi_full", data + EOI, 97, candidate_kind="synthetic_header", provenance=[{"kind": "append", "value": "EOI"}])
        add("prepend_soi_append_eoi_full", SOI + data + EOI, 96, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "append", "value": "EOI"}])

        soi_positions = sample_positions(find_all(data, SOI), 12)
        eoi_positions = find_all(data, EOI)
        sos_positions = sample_positions(find_all(data, SOS), 12)
        marker_positions: list[int] = []
        for marker in [APP0, APP1, DQT, DHT, DRI, *JPEG_SOF_MARKERS, SOS]:
            marker_positions.extend(find_all(data, marker))
        marker_positions = sample_positions(sorted(set(marker_positions)), 20)
        rst_positions = sorted(find_all(data, b"\xff\xd0") + find_all(data, b"\xff\xd1") + find_all(data, b"\xff\xd2") + find_all(data, b"\xff\xd3") + find_all(data, b"\xff\xd4") + find_all(data, b"\xff\xd5") + find_all(data, b"\xff\xd6") + find_all(data, b"\xff\xd7"))

        for soi in soi_positions:
            later_eois = [e for e in eoi_positions if e > soi]
            for eoi in sample_positions(later_eois, 5):
                add("soi_to_sampled_eoi", data[soi:eoi + 2], 95, provenance=[{"kind": "slice", "start": soi, "end": eoi + 2}], start=soi, end=eoi + 2)
            add("soi_to_end", data[soi:], 94, provenance=[{"kind": "slice", "start": soi, "end": None}], start=soi)
            add("soi_to_end_append_eoi", data[soi:] + EOI, 93, candidate_kind="synthetic_header", provenance=[{"kind": "slice", "start": soi, "end": None}, {"kind": "append", "value": "EOI"}], start=soi)
            for tail_len in (65536, 262144, 1048576):
                end = min(len(data), soi + tail_len)
                if end - soi >= 128:
                    add(f"soi_tail_{tail_len}", data[soi:end], 92, provenance=[{"kind": "slice", "start": soi, "end": end}], start=soi, end=end)
                    add(f"soi_tail_{tail_len}_append_eoi", data[soi:end] + EOI, 91, candidate_kind="synthetic_header", provenance=[{"kind": "slice", "start": soi, "end": end}, {"kind": "append", "value": "EOI"}], start=soi, end=end)

        for pos in marker_positions:
            for back in (0, 128, 512, 2048, 8192, 32768):
                start = max(0, pos - back)
                add(f"synthetic_soi_back_{back}", SOI + data[start:], 88, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": None}], start=start)
                add(f"synthetic_soi_back_{back}_append_eoi", SOI + data[start:] + EOI, 87, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": None}, {"kind": "append", "value": "EOI"}], start=start)
                later_eois = [e for e in eoi_positions if e > pos]
                for eoi in sample_positions(later_eois, 3):
                    add(f"synthetic_soi_back_{back}_to_eoi", SOI + data[start:eoi + 2], 86, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": eoi + 2}], start=start, end=eoi + 2)

        dht_blob = standard_dht_segments()
        if dht_blob and stats["sos_count"] > 0 and stats["dht_count"] == 0:
            for sos in sos_positions:
                repaired = data[:sos] + dht_blob + data[sos:]
                add("inject_standard_dht_before_sos", repaired, 99, candidate_kind="synthetic_header", provenance=[{"kind": "insert", "offset": sos, "value": "DHT"}], sos=sos)
                add("inject_standard_dht_before_sos_append_eoi", repaired + EOI, 98, candidate_kind="synthetic_header", provenance=[{"kind": "insert", "offset": sos, "value": "DHT"}, {"kind": "append", "value": "EOI"}], sos=sos)
                add("prepend_soi_inject_standard_dht_before_sos", SOI + repaired, 97, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "insert", "offset": sos, "value": "DHT"}], sos=sos)
                add("prepend_soi_inject_standard_dht_before_sos_append_eoi", SOI + repaired + EOI, 96, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "insert", "offset": sos, "value": "DHT"}, {"kind": "append", "value": "EOI"}], sos=sos)

        for sos in sos_positions:
            later_eois = [e for e in eoi_positions if e > sos]
            app_blob, dqt_blob, sof_blob, dht_or_default, dri_blob = _extract_rebuild_segments(data, sos)
            if dqt_blob and sof_blob:
                scan_slices: list[tuple[int | None, bytes]] = []
                if later_eois:
                    for eoi in sample_positions(later_eois, 3):
                        scan_slices.append((eoi + 2, data[sos:eoi + 2]))
                scan_slices.append((None, data[sos:] + (b"" if data.endswith(EOI) else EOI)))
                for end, scan_data in scan_slices:
                    header = SOI + app_blob + dqt_blob + sof_blob + dht_or_default + dri_blob
                    add(
                        "rebuild_header_from_segments",
                        header + scan_data,
                        108 if classification.label == "jpeg_missing_soi_internal_structure" else 101,
                        candidate_kind="synthetic_header",
                        provenance=[
                            {"kind": "rebuild_header", "sos": sos, "scan_end": end, "has_dqt": bool(dqt_blob), "has_sof": bool(sof_blob), "has_dht": bool(dht_or_default)},
                        ],
                        sos=sos,
                        end=end,
                    )
                    add(
                        "rebuild_header_from_segments_no_app",
                        SOI + dqt_blob + sof_blob + dht_or_default + dri_blob + scan_data,
                        100,
                        candidate_kind="synthetic_header",
                        provenance=[{"kind": "rebuild_header_minimal", "sos": sos, "scan_end": end}],
                        sos=sos,
                        end=end,
                    )

        if rst_positions and sos_positions:
            for sos in sos_positions[:4]:
                later_rsts = [rst for rst in rst_positions if rst > sos]
                for rst in sample_positions(later_rsts, 4):
                    end = min(len(data), rst + 2)
                    scan = data[sos:end] + EOI
                    app_blob, dqt_blob, sof_blob, dht_or_default, dri_blob = _extract_rebuild_segments(data, sos)
                    if dqt_blob and sof_blob:
                        add(
                            "restart_window_rebuild_header",
                            SOI + app_blob + dqt_blob + sof_blob + dht_or_default + dri_blob + scan,
                            99,
                            candidate_kind="synthetic_header",
                            provenance=[{"kind": "restart_window", "sos": sos, "rst_end": end}],
                            sos=sos,
                            end=end,
                        )

        if classification.label == "jpeg_missing_eoi":
            add("classification_hint_append_eoi", data + EOI, 105, candidate_kind="synthetic_header")
        elif classification.label == "jpeg_missing_soi_internal_structure":
            for pos in marker_positions[:8]:
                start = max(0, pos - 2048)
                add("classification_hint_synthetic_soi", SOI + data[start:], 104, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": None}], start=start)
        elif classification.label == "jpeg_missing_dht" and dht_blob and sos_positions:
            sos = sos_positions[0]
            add("classification_hint_inject_standard_dht", data[:sos] + dht_blob + data[sos:], 106, candidate_kind="synthetic_header", provenance=[{"kind": "insert", "offset": sos, "value": "DHT"}], sos=sos)

        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.strategy_id))
        return candidates
