from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image

from ..classification import jpeg_marker_stats
from ..constants import APP0, APP1, DHT, DQT, DRI, EOI, JPEG_SOF_MARKERS, SOI, SOS
from ..signature_index import find_all, sample_positions
from ..types import Candidate, Classification, FileRecord
from .base import RecoveryEngine


APP_MARKERS = [bytes([0xFF, marker]) for marker in range(0xE0, 0xF0)]
COM = b"\xff\xfe"
HEADER_MARKERS = {DQT, DHT, DRI, COM, *APP_MARKERS, *JPEG_SOF_MARKERS}


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


def _scan_complete_segments_anywhere(data: bytes, markers: set[bytes], limit_per_marker: int = 12) -> dict[bytes, list[tuple[int, bytes]]]:
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


def _nearest_segments(segments: list[tuple[int, bytes]], target: int, limit: int = 2) -> list[tuple[int, bytes]]:
    if not segments:
        return []
    ranked = sorted(segments, key=lambda item: (abs(target - item[0]), item[0]))
    return ranked[:limit]


@lru_cache(maxsize=16)
def _jpeg_sample_bytes(component_count: int, quality: int) -> bytes:
    mode = "L" if component_count <= 1 else "RGB"
    fill = 128 if mode == "L" else (128, 128, 128)
    img = Image.new(mode, (16, 16), fill)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


@lru_cache(maxsize=16)
def standard_dht_segments(component_count: int = 3) -> bytes:
    sample = _jpeg_sample_bytes(1 if component_count <= 1 else 3, 75)
    segments = _extract_jpeg_segments(sample, DHT)
    return b"".join(segments)


@lru_cache(maxsize=32)
def standard_dqt_segments(component_count: int = 3, quality: int = 75) -> bytes:
    sample = _jpeg_sample_bytes(1 if component_count <= 1 else 3, quality)
    segments = _extract_jpeg_segments(sample, DQT)
    return b"".join(segments)


@lru_cache(maxsize=4)
def standard_app0_segment(component_count: int = 3) -> bytes:
    sample = _jpeg_sample_bytes(1 if component_count <= 1 else 3, 75)
    segments = _extract_jpeg_segments(sample, APP0)
    return segments[0] if segments else b""


def _parse_sof_component_ids(sof_segment: bytes) -> list[int]:
    if len(sof_segment) < 10 or sof_segment[:2] not in JPEG_SOF_MARKERS:
        return []
    component_count = sof_segment[9]
    expected = 10 + component_count * 3
    if len(sof_segment) < expected:
        return []
    return [sof_segment[10 + (index * 3)] for index in range(component_count)]


@lru_cache(maxsize=64)
def _synthetic_sos_from_sof(sof_segment: bytes) -> bytes:
    component_ids = _parse_sof_component_ids(sof_segment)
    if not component_ids:
        return b""

    payload = bytearray()
    payload.extend(SOS)
    payload.extend((6 + 2 * len(component_ids)).to_bytes(2, "big"))
    for index, component_id in enumerate(component_ids):
        if len(component_ids) == 1:
            selector = 0x00
        elif index == 0:
            selector = 0x00
        else:
            selector = 0x11
        payload.extend((component_id, selector))
    payload.extend((0x00, 0x3F, 0x00))
    return bytes(payload)


def _expected_table_counts(component_count: int) -> tuple[int, int]:
    if component_count <= 1:
        return 1, 2
    return 2, 4


@lru_cache(maxsize=16)
def _standard_dqt_profiles(component_count: int) -> tuple[tuple[str, bytes], ...]:
    qualities = (75, 85, 95)
    profiles: list[tuple[str, bytes]] = []
    for quality in qualities:
        blob = standard_dqt_segments(component_count, quality)
        if blob:
            label = f"std_{'gray' if component_count <= 1 else 'color'}_q{quality}"
            profiles.append((label, blob))
    return tuple(profiles)


@lru_cache(maxsize=4)
def _standard_dht_profile(component_count: int) -> tuple[str, bytes]:
    label = f"std_{'gray' if component_count <= 1 else 'color'}"
    return label, standard_dht_segments(component_count)


@lru_cache(maxsize=4)
def _standard_app_profile(component_count: int) -> bytes:
    return standard_app0_segment(component_count)



def _extract_rebuild_options(data: bytes, target_offset: int) -> list[dict[str, object]]:
    found = _scan_complete_segments_anywhere(data, HEADER_MARKERS)

    sof_entries: list[tuple[int, bytes]] = []
    for marker in JPEG_SOF_MARKERS:
        sof_entries.extend(_nearest_segments(found.get(marker, []), target_offset, limit=2))

    unique_sof: list[tuple[int, bytes]] = []
    seen_sof: set[bytes] = set()
    for offset, segment in sorted(sof_entries, key=lambda item: (abs(target_offset - item[0]), item[0])):
        if segment in seen_sof:
            continue
        seen_sof.add(segment)
        unique_sof.append((offset, segment))
    sof_entries = unique_sof[:4]

    if not sof_entries:
        return []

    options: list[dict[str, object]] = []
    seen_option_keys: set[tuple[bytes, bytes, bytes, bytes, bytes, str]] = set()

    for sof_offset, sof_blob in sof_entries:
        component_ids = _parse_sof_component_ids(sof_blob)
        component_count = max(1, len(component_ids) or 1)
        expected_dqt_count, expected_dht_count = _expected_table_counts(component_count)
        synthetic_sos = _synthetic_sos_from_sof(sof_blob)

        app_segments: list[bytes] = []
        app_offsets: list[int] = []
        for marker in APP_MARKERS:
            nearest = _nearest_segments(found.get(marker, []), sof_offset, limit=1)
            for offset, segment in nearest:
                app_offsets.append(offset)
                app_segments.append(segment)
        app_segments = app_segments[:2]
        if not app_segments:
            std_app = _standard_app_profile(component_count)
            if std_app:
                app_segments = [std_app]

        dqt_exact = [
            (f"found_dqt_{count}", b"".join(segment for _, segment in found.get(DQT, [])[:count]))
            for count in (expected_dqt_count, 1, 2, 4)
            if found.get(DQT, []) and count <= max(1, len(found.get(DQT, [])))
        ]
        dht_exact = [
            (f"found_dht_{count}", b"".join(segment for _, segment in found.get(DHT, [])[:count]))
            for count in (expected_dht_count, 2, 4, 1)
            if found.get(DHT, []) and count <= max(1, len(found.get(DHT, [])))
        ]

        dqt_options: list[tuple[str, bytes]] = []
        dht_options: list[tuple[str, bytes]] = []
        seen_dqt: set[bytes] = set()
        seen_dht: set[bytes] = set()
        for label, blob in [*dqt_exact, *_standard_dqt_profiles(component_count)]:
            if blob and blob not in seen_dqt:
                seen_dqt.add(blob)
                dqt_options.append((label, blob))
        for label, blob in [*dht_exact, _standard_dht_profile(component_count)]:
            if blob and blob not in seen_dht:
                seen_dht.add(blob)
                dht_options.append((label, blob))

        dri_candidates = _nearest_segments(found.get(DRI, []), sof_offset, limit=1)
        dri_options = [(f"found_dri", offset, segment) for offset, segment in dri_candidates] or [("none", -1, b"")]

        for dqt_label, dqt_blob in dqt_options[:3]:
            for dht_label, dht_blob in dht_options[:2]:
                for dri_label, dri_offset, dri_blob in dri_options[:1]:
                    app_blob = b"".join(app_segments[:2])
                    key = (app_blob, dqt_blob, sof_blob, dht_blob, dri_blob, f"{dqt_label}|{dht_label}|{dri_label}")
                    if key in seen_option_keys:
                        continue
                    seen_option_keys.add(key)
                    options.append(
                        {
                            "app": app_blob,
                            "dqt": dqt_blob,
                            "sof": sof_blob,
                            "dht": dht_blob,
                            "dri": dri_blob,
                            "sof_offset": sof_offset,
                            "dri_offset": dri_offset,
                            "app_offsets": app_offsets[:2],
                            "synthetic_sos": synthetic_sos,
                            "component_count": component_count,
                            "table_profile": f"{dqt_label}__{dht_label}",
                        }
                    )
    return options[:18]


def _bounded_scan_windows(data: bytes, sos: int, eoi_positions: list[int]) -> list[tuple[int | None, bytes]]:
    windows: list[tuple[int | None, bytes]] = []
    later_eois = [eoi for eoi in eoi_positions if eoi > sos]
    for eoi in sample_positions(later_eois, 4):
        windows.append((eoi + 2, data[sos:eoi + 2]))
    for length in (65536, 262144, 1048576, 4194304):
        end = min(len(data), sos + length)
        if end - sos >= 128:
            windows.append((end, data[sos:end] + EOI))
    windows.append((None, data[sos:] + (b"" if data.endswith(EOI) else EOI)))
    deduped: list[tuple[int | None, bytes]] = []
    seen: set[tuple[int | None, int]] = set()
    for end, scan in windows:
        key = (end, len(scan))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((end, scan))
    return deduped


def _bounded_windows_from_starts(data: bytes, starts: list[int], eoi_positions: list[int]) -> list[tuple[int, int | None, bytes]]:
    windows: list[tuple[int, int | None, bytes]] = []
    seen: set[tuple[int, int | None, int]] = set()
    for start in starts:
        if start >= len(data) - 64:
            continue
        later_eois = [eoi for eoi in eoi_positions if eoi > start]
        for eoi in sample_positions(later_eois, 3):
            payload = data[start:eoi + 2]
            key = (start, eoi + 2, len(payload))
            if key not in seen and len(payload) >= 128:
                seen.add(key)
                windows.append((start, eoi + 2, payload))
        for length in (65536, 262144, 1048576, 4194304):
            end = min(len(data), start + length)
            if end - start < 128:
                continue
            payload = data[start:end] + EOI
            key = (start, end, len(payload))
            if key not in seen:
                seen.add(key)
                windows.append((start, end, payload))
        payload = data[start:] + (b"" if data.endswith(EOI) else EOI)
        key = (start, None, len(payload))
        if key not in seen and len(payload) >= 128:
            seen.add(key)
            windows.append((start, None, payload))
    return windows


def _synthetic_sos_scan_starts(
    data: bytes,
    sof_offset: int,
    sof_segment: bytes,
    found_segments: dict[bytes, list[tuple[int, bytes]]],
    rst_positions: list[int],
) -> list[int]:
    starts: list[int] = []
    sof_end = sof_offset + len(sof_segment)
    starts.append(sof_end)

    nearby_header_ends: list[int] = []
    for marker in HEADER_MARKERS:
        for offset, segment in found_segments.get(marker, []):
            if abs(offset - sof_offset) <= 131072:
                nearby_header_ends.append(offset + len(segment))
    if nearby_header_ends:
        starts.extend(sorted(nearby_header_ends)[-3:])

    later_rsts = [rst for rst in rst_positions if rst > sof_end]
    for rst in sample_positions(later_rsts, 4):
        for back in (256, 1024, 4096, 16384, 65536):
            starts.append(max(sof_end, rst - back))

    deduped: list[int] = []
    seen: set[int] = set()
    for start in starts:
        if start in seen:
            continue
        seen.add(start)
        deduped.append(start)
    return [start for start in deduped if 0 <= start < len(data) - 64]


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

        soi_positions = sample_positions(find_all(data, SOI), 16)
        eoi_positions = find_all(data, EOI)
        sos_positions = sample_positions(find_all(data, SOS), 16)
        marker_positions: list[int] = []
        for marker in [*APP_MARKERS, DQT, DHT, DRI, *JPEG_SOF_MARKERS, SOS]:
            marker_positions.extend(find_all(data, marker))
        marker_positions = sample_positions(sorted(set(marker_positions)), 32)
        rst_positions = sorted(
            find_all(data, b"\xff\xd0") + find_all(data, b"\xff\xd1") + find_all(data, b"\xff\xd2") + find_all(data, b"\xff\xd3") +
            find_all(data, b"\xff\xd4") + find_all(data, b"\xff\xd5") + find_all(data, b"\xff\xd6") + find_all(data, b"\xff\xd7")
        )

        for soi in soi_positions:
            later_eois = [e for e in eoi_positions if e > soi]
            for eoi in sample_positions(later_eois, 6):
                add("soi_to_sampled_eoi", data[soi:eoi + 2], 95, provenance=[{"kind": "slice", "start": soi, "end": eoi + 2}], start=soi, end=eoi + 2)
            add("soi_to_end", data[soi:], 94, provenance=[{"kind": "slice", "start": soi, "end": None}], start=soi)
            add("soi_to_end_append_eoi", data[soi:] + EOI, 93, candidate_kind="synthetic_header", provenance=[{"kind": "slice", "start": soi, "end": None}, {"kind": "append", "value": "EOI"}], start=soi)
            for tail_len in (65536, 262144, 1048576, 4194304):
                end = min(len(data), soi + tail_len)
                if end - soi >= 128:
                    add(f"soi_tail_{tail_len}", data[soi:end], 92, provenance=[{"kind": "slice", "start": soi, "end": end}], start=soi, end=end)
                    add(f"soi_tail_{tail_len}_append_eoi", data[soi:end] + EOI, 91, candidate_kind="synthetic_header", provenance=[{"kind": "slice", "start": soi, "end": end}, {"kind": "append", "value": "EOI"}], start=soi, end=end)

        for pos in marker_positions:
            later_eois = [e for e in eoi_positions if e > pos]
            for back in (0, 128, 512, 2048, 8192, 32768, 131072):
                start = max(0, pos - back)
                add(f"synthetic_soi_back_{back}", SOI + data[start:], 88, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": None}], start=start)
                add(f"synthetic_soi_back_{back}_append_eoi", SOI + data[start:] + EOI, 87, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": None}, {"kind": "append", "value": "EOI"}], start=start)
                for eoi in sample_positions(later_eois, 3):
                    add(f"synthetic_soi_back_{back}_to_eoi", SOI + data[start:eoi + 2], 86, candidate_kind="synthetic_header", provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": eoi + 2}], start=start, end=eoi + 2)

        found_segments = _scan_complete_segments_anywhere(data, HEADER_MARKERS)
        if stats["sos_count"] > 0 and (stats["dht_count"] == 0 or stats["dqt_count"] == 0):
            sof_entries: list[tuple[int, bytes]] = []
            for marker in JPEG_SOF_MARKERS:
                sof_entries.extend(found_segments.get(marker, []))
            for sos in sos_positions:
                nearest_sof = _nearest_segments(sof_entries, sos, limit=1)
                component_count = 3
                if nearest_sof:
                    component_count = max(1, len(_parse_sof_component_ids(nearest_sof[0][1])) or 1)
                dqt_profiles = _standard_dqt_profiles(component_count)
                dht_label, dht_blob = _standard_dht_profile(component_count)
                for dqt_label, dqt_blob in dqt_profiles[:3]:
                    repaired = data
                    insertions: list[dict[str, object]] = []
                    header_prefix = b""
                    if stats["dqt_count"] == 0 and dqt_blob:
                        repaired = repaired[:sos] + dqt_blob + repaired[sos:]
                        insertions.append({"kind": "insert", "offset": sos, "value": dqt_label})
                        sos_shift = len(dqt_blob)
                    else:
                        sos_shift = 0
                    if stats["dht_count"] == 0 and dht_blob:
                        repaired = repaired[:sos + sos_shift] + dht_blob + repaired[sos + sos_shift:]
                        insertions.append({"kind": "insert", "offset": sos + sos_shift, "value": dht_label})
                    if stats["soi_count"] == 0:
                        header_prefix = SOI
                    if insertions:
                        suffix = f"{dqt_label}__{dht_label}" if stats["dqt_count"] == 0 else dht_label
                        add(f"inject_standard_tables_before_sos_{suffix}", header_prefix + repaired, 103, candidate_kind="synthetic_header", provenance=([{"kind": "prepend", "value": "SOI"}] if header_prefix else []) + insertions, sos=sos, component_count=component_count)
                        add(f"inject_standard_tables_before_sos_append_eoi_{suffix}", header_prefix + repaired + EOI, 102, candidate_kind="synthetic_header", provenance=([{"kind": "prepend", "value": "SOI"}] if header_prefix else []) + insertions + [{"kind": "append", "value": "EOI"}], sos=sos, component_count=component_count)

        # Found segments are reused by the rebuild lanes below.

        for sos in sos_positions:
            rebuild_options = _extract_rebuild_options(data, sos)
            if not rebuild_options:
                continue

            scan_windows = _bounded_scan_windows(data, sos, eoi_positions)
            for rebuild_index, option in enumerate(rebuild_options):
                header = SOI + bytes(option["app"]) + bytes(option["dqt"]) + bytes(option["sof"]) + bytes(option["dht"]) + bytes(option["dri"])
                minimal_header = SOI + bytes(option["dqt"]) + bytes(option["sof"]) + bytes(option["dht"]) + bytes(option["dri"])
                for end, scan_data in scan_windows:
                    profile_suffix = str(option.get("table_profile") or "found")
                    add(
                        f"rebuild_header_from_segments_{profile_suffix}",
                        header + scan_data,
                        109 if classification.label == "jpeg_missing_soi_internal_structure" else 101,
                        candidate_kind="synthetic_header",
                        provenance=[{"kind": "rebuild_header", "sos": sos, "scan_end": end, "rebuild_index": rebuild_index}],
                        sos=sos,
                        end=end,
                    )
                    add(
                        f"rebuild_header_from_segments_minimal_{profile_suffix}",
                        minimal_header + scan_data,
                        100,
                        candidate_kind="synthetic_header",
                        provenance=[{"kind": "rebuild_header_minimal", "sos": sos, "scan_end": end, "rebuild_index": rebuild_index}],
                        sos=sos,
                        end=end,
                    )

                    for start_back in (0, 128, 512, 2048, 8192):
                        start = max(0, sos - start_back)
                        prefixed_scan = data[start:sos] + scan_data
                        add(
                            f"sos_window_rebuild_header_back_{start_back}_{profile_suffix}",
                            header + prefixed_scan,
                            99,
                            candidate_kind="synthetic_header",
                            provenance=[{"kind": "sos_window_rebuild", "start": start, "sos": sos, "scan_end": end, "rebuild_index": rebuild_index}],
                            start=start,
                            sos=sos,
                            end=end,
                        )

        # New high-value lane: files with SOF/restart structure but no SOS.
        # The v3 run plateau strongly suggests many dominant failures are in this class.
        if classification.label == "jpeg_missing_soi_internal_structure" and not sos_positions:
            rebuild_options = _extract_rebuild_options(data, marker_positions[0] if marker_positions else 0)
            for rebuild_index, option in enumerate(rebuild_options):
                synthetic_sos = bytes(option.get("synthetic_sos") or b"")
                sof_segment = bytes(option["sof"])
                sof_offset = int(option.get("sof_offset") or 0)
                if not synthetic_sos:
                    continue
                scan_starts = _synthetic_sos_scan_starts(data, sof_offset, sof_segment, found_segments, rst_positions)
                scan_windows = _bounded_windows_from_starts(data, scan_starts, eoi_positions)
                if not scan_windows:
                    continue

                header = SOI + bytes(option["app"]) + bytes(option["dqt"]) + sof_segment + bytes(option["dht"]) + bytes(option["dri"])
                minimal_header = SOI + bytes(option["dqt"]) + sof_segment + bytes(option["dht"]) + bytes(option["dri"])
                for start, end, scan_data in scan_windows:
                    profile_suffix = str(option.get("table_profile") or "found")
                    add(
                        f"rebuild_header_with_synthetic_sos_{profile_suffix}",
                        header + synthetic_sos + scan_data,
                        111,
                        candidate_kind="synthetic_header",
                        provenance=[
                            {"kind": "rebuild_header_with_synthetic_sos", "sof_offset": sof_offset, "scan_start": start, "scan_end": end, "rebuild_index": rebuild_index},
                        ],
                        sof_offset=sof_offset,
                        scan_start=start,
                        scan_end=end,
                    )
                    add(
                        f"rebuild_header_with_synthetic_sos_minimal_{profile_suffix}",
                        minimal_header + synthetic_sos + scan_data,
                        110,
                        candidate_kind="synthetic_header",
                        provenance=[
                            {"kind": "rebuild_header_with_synthetic_sos_minimal", "sof_offset": sof_offset, "scan_start": start, "scan_end": end, "rebuild_index": rebuild_index},
                        ],
                        sof_offset=sof_offset,
                        scan_start=start,
                        scan_end=end,
                    )
                    if rst_positions:
                        add(
                            f"rebuild_header_with_synthetic_sos_rst_window_{profile_suffix}",
                            header + synthetic_sos + scan_data,
                            112,
                            candidate_kind="synthetic_header",
                            provenance=[
                                {"kind": "rebuild_header_with_synthetic_sos_rst_window", "sof_offset": sof_offset, "scan_start": start, "scan_end": end, "rebuild_index": rebuild_index},
                            ],
                            sof_offset=sof_offset,
                            scan_start=start,
                            scan_end=end,
                        )

        if rst_positions and sos_positions:
            for sos in sos_positions[:8]:
                later_rsts = [rst for rst in rst_positions if rst > sos]
                for rst in sample_positions(later_rsts, 8):
                    end = min(len(data), rst + 2)
                    scan = data[sos:end] + EOI
                    for rebuild_index, option in enumerate(_extract_rebuild_options(data, sos)[:3]):
                        header = SOI + bytes(option["app"]) + bytes(option["dqt"]) + bytes(option["sof"]) + bytes(option["dht"]) + bytes(option["dri"])
                        profile_suffix = str(option.get("table_profile") or "found")
                        add(
                            f"restart_window_rebuild_header_{profile_suffix}",
                            header + scan,
                            99,
                            candidate_kind="synthetic_header",
                            provenance=[{"kind": "restart_window", "sos": sos, "rst_end": end, "rebuild_index": rebuild_index}],
                            sos=sos,
                            end=end,
                        )

        if classification.label == "jpeg_missing_eoi":
            add("classification_hint_append_eoi", data + EOI, 105, candidate_kind="synthetic_header")
        elif classification.label == "jpeg_missing_soi_internal_structure":
            for pos in marker_positions[:16]:
                for back in (512, 2048, 8192, 32768):
                    start = max(0, pos - back)
                    add(
                        f"classification_hint_synthetic_soi_back_{back}",
                        SOI + data[start:],
                        106,
                        candidate_kind="synthetic_header",
                        provenance=[{"kind": "prepend", "value": "SOI"}, {"kind": "slice", "start": start, "end": None}],
                        start=start,
                    )
        elif classification.label == "jpeg_missing_dht" and sos_positions:
            for sos in sos_positions[:4]:
                sof_entries: list[tuple[int, bytes]] = []
                for marker in JPEG_SOF_MARKERS:
                    sof_entries.extend(found_segments.get(marker, []))
                nearest_sof = _nearest_segments(sof_entries, sos, limit=1)
                component_count = 3
                if nearest_sof:
                    component_count = max(1, len(_parse_sof_component_ids(nearest_sof[0][1])) or 1)
                dht_label, dht_blob = _standard_dht_profile(component_count)
                if dht_blob:
                    add(
                        f"classification_hint_inject_standard_dht_{dht_label}",
                        data[:sos] + dht_blob + data[sos:],
                        107,
                        candidate_kind="synthetic_header",
                        provenance=[{"kind": "insert", "offset": sos, "value": dht_label}],
                        sos=sos,
                        component_count=component_count,
                    )

        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.strategy_id))
        return candidates
