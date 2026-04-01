from __future__ import annotations

from .constants import (
    APP0,
    APP1,
    BMP_SIG,
    DHT,
    DQT,
    EOI,
    GIF87A,
    GIF89A,
    JPEG_SOF_MARKERS,
    PNG_IDAT,
    PNG_IEND,
    PNG_IHDR,
    PNG_SIG,
    RIFF,
    SOI,
    SOS,
    TIFF_BE,
    TIFF_LE,
    WEBP,
)
from .types import Classification, FileRecord


def find_all(data: bytes, needle: bytes) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1
    return positions


def jpeg_marker_stats(data: bytes) -> dict[str, int]:
    stats = {
        "soi_count": len(find_all(data, SOI)),
        "eoi_count": len(find_all(data, EOI)),
        "sos_count": len(find_all(data, SOS)),
        "dqt_count": len(find_all(data, DQT)),
        "dht_count": len(find_all(data, DHT)),
        "app0_count": len(find_all(data, APP0)),
        "app1_count": len(find_all(data, APP1)),
        "sof_count": sum(len(find_all(data, marker)) for marker in JPEG_SOF_MARKERS),
    }
    rst_total = 0
    for i in range(8):
        rst_total += len(find_all(data, bytes([0xFF, 0xD0 + i])))
    stats["rst_count"] = rst_total
    stats["internal_marker_count"] = (
        stats["sos_count"]
        + stats["dqt_count"]
        + stats["dht_count"]
        + stats["sof_count"]
        + stats["app0_count"]
        + stats["app1_count"]
    )
    return stats


def other_marker_stats(data: bytes) -> dict[str, dict[str, int]]:
    return {
        "png": {
            "png_sig_count": len(find_all(data, PNG_SIG)),
            "ihdr_count": len(find_all(data, PNG_IHDR)),
            "idat_count": len(find_all(data, PNG_IDAT)),
            "iend_count": len(find_all(data, PNG_IEND)),
        },
        "gif": {
            "gif_header_count": len(find_all(data, GIF87A)) + len(find_all(data, GIF89A)),
        },
        "bmp": {
            "bm_count": len(find_all(data, BMP_SIG)),
        },
        "tiff": {
            "tiff_header_count": len(find_all(data, TIFF_LE)) + len(find_all(data, TIFF_BE)),
        },
        "webp": {
            "riff_count": len(find_all(data, RIFF)),
            "webp_count": len(find_all(data, WEBP)),
        },
    }


def classify_record(record: FileRecord, data: bytes) -> Classification:
    jpeg_stats = jpeg_marker_stats(data)
    auxiliary = other_marker_stats(data)

    declared_jpeg = record.declared_kind == "jpeg"
    byte0_jpeg = record.byte0_kind == "jpeg"
    internal_jpeg = jpeg_stats["internal_marker_count"] > 0

    jpeg_evidence = 0.0
    if declared_jpeg:
        jpeg_evidence += 0.45
    if byte0_jpeg:
        jpeg_evidence += 0.4
    if internal_jpeg:
        jpeg_evidence += 0.25
    if jpeg_stats["soi_count"] > 0:
        jpeg_evidence += 0.1
    if jpeg_stats["sos_count"] > 0:
        jpeg_evidence += 0.15
    jpeg_evidence = min(jpeg_evidence, 0.99)

    if declared_jpeg or byte0_jpeg or internal_jpeg:
        if jpeg_stats["soi_count"] == 0 and jpeg_stats["internal_marker_count"] > 0:
            label = "jpeg_missing_soi_internal_structure"
            confidence = max(jpeg_evidence, 0.82)
        elif jpeg_stats["soi_count"] > 0 and jpeg_stats["eoi_count"] == 0:
            label = "jpeg_missing_eoi"
            confidence = max(jpeg_evidence, 0.85)
        elif jpeg_stats["sos_count"] > 0 and jpeg_stats["dht_count"] == 0:
            label = "jpeg_missing_dht"
            confidence = max(jpeg_evidence, 0.84)
        elif jpeg_stats["soi_count"] > 0 and jpeg_stats["sos_count"] > 0:
            label = "jpeg_structural_salvage_candidate"
            confidence = max(jpeg_evidence, 0.75)
        elif jpeg_stats["internal_marker_count"] > 0:
            label = "jpeg_internal_weak_signal"
            confidence = max(jpeg_evidence, 0.65)
        else:
            label = "jpeg_low_signal"
            confidence = max(jpeg_evidence, 0.5)

        return Classification(
            family="jpeg",
            label=label,
            confidence=round(confidence, 4),
            evidence={
                "declared_kind": record.declared_kind,
                "byte0_kind": record.byte0_kind,
                "jpeg": jpeg_stats,
                **auxiliary,
            },
        )

    if record.declared_kind:
        return Classification(
            family=record.declared_kind,
            label=f"{record.declared_kind}_declared_only",
            confidence=0.55,
            evidence={
                "declared_kind": record.declared_kind,
                "byte0_kind": record.byte0_kind,
                "jpeg": jpeg_stats,
                **auxiliary,
            },
        )

    return Classification(
        family="unknown",
        label="unknown_low_signal",
        confidence=0.2,
        evidence={
            "declared_kind": record.declared_kind,
            "byte0_kind": record.byte0_kind,
            "jpeg": jpeg_stats,
            **auxiliary,
        },
    )
