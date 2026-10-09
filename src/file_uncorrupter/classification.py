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
    AUDIO_KINDS,
    ARCHIVE_KINDS,
    DOCUMENT_KINDS,
    PACKAGE_KINDS,
    TEXT_KINDS,
)
from .signature_index import find_all
from .types import Classification, FileRecord


ISOBMFF_FAMILIES = {"mp4", "mov", "heif", "avif", "jp2"}
VIDEO_FAMILIES = {"mp4", "mov", "avi", "mkv", "webm", "mpegts", "mpegps", "flv", "asf", "wmv"}


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


def _generic_evidence(record: FileRecord, jpeg_stats: dict[str, int], auxiliary: dict[str, dict[str, int]]) -> dict[str, object]:
    return {
        "declared_kind": record.declared_kind,
        "byte0_kind": record.byte0_kind,
        "anywhere_kind": record.anywhere_kind,
        "signature_summary": record.signature_summary,
        "signature_hits": [
            {
                "family": hit.family,
                "signature_type": hit.signature_type,
                "offset": hit.offset,
                "confidence": hit.confidence,
            }
            for hit in record.signature_hits[:32]
        ],
        "jpeg": jpeg_stats,
        "extension_evidence": {"declared_kind": record.declared_kind, "suffix": record.path.suffix.lower()},
        "signature_evidence": {
            "byte0_kind": record.byte0_kind,
            "anywhere_kind": record.anywhere_kind,
            "hits": len(record.signature_hits),
        },
        "structure_evidence": {"jpeg": jpeg_stats, **auxiliary},
        **auxiliary,
    }


def classify_record(record: FileRecord, data: bytes) -> Classification:
    jpeg_stats = jpeg_marker_stats(data)
    auxiliary = other_marker_stats(data)
    evidence = _generic_evidence(record, jpeg_stats, auxiliary)

    declared_jpeg = record.declared_kind == "jpeg"
    declared_video = record.declared_kind in VIDEO_FAMILIES
    byte0_jpeg = record.byte0_kind == "jpeg"
    strong_anywhere_jpeg = any(hit.family == "jpeg" for hit in record.signature_hits)
    internal_jpeg = strong_anywhere_jpeg or (
        jpeg_stats["sos_count"] > 0
        and (jpeg_stats["dqt_count"] > 0 or jpeg_stats["dht_count"] > 0 or jpeg_stats["sof_count"] > 0 or jpeg_stats["rst_count"] > 0)
    )

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

    # Video containers can legitimately embed JPEG frames or thumbnails, and
    # random/corrupt payloads can contain short JPEG marker collisions. Only a
    # JPEG signature at byte zero may override a declared video family.
    jpeg_candidate = declared_jpeg or byte0_jpeg or (internal_jpeg and not declared_video)

    if jpeg_candidate:
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
        return Classification(family="jpeg", label=label, confidence=round(confidence, 4), evidence=evidence)

    if record.declared_kind in PACKAGE_KINDS and (record.byte0_kind == "zip" or record.anywhere_kind == "zip"):
        return Classification(
            family=record.declared_kind,
            label=f"{record.declared_kind}_zip_package_candidate",
            confidence=0.92,
            evidence=evidence,
        )

    # Some public variants intentionally share a container signature. Preserve
    # the declared variant when the extension and container evidence agree;
    # treating every OLE file as DOC, every TIFF-based camera file as TIFF, or
    # every ASF container as ASF would make advertised XLS/PPT/RAW/WMV routes
    # unreachable despite valid suffix evidence.
    declared_container_aliases = {
        "doc": {"doc", "xls", "ppt"},
        "tiff": {"raw"},
        "asf": {"wmv"},
    }
    compatible_declared = declared_container_aliases.get(record.byte0_kind, set())
    if record.declared_kind in compatible_declared:
        return Classification(
            family=str(record.declared_kind),
            label=f"{record.declared_kind}_{record.byte0_kind}_container_candidate",
            confidence=0.88,
            evidence=evidence,
        )

    if record.declared_kind in TEXT_KINDS and record.byte0_kind in {"unknown", "text"}:
        confidence = 0.9 if record.byte0_kind == "text" else 0.68
        return Classification(
            family=record.declared_kind,
            label=f"{record.declared_kind}_text_candidate",
            confidence=confidence,
            evidence=evidence,
        )

    if record.byte0_kind != "unknown":
        inferred_family = record.byte0_kind
    elif record.anywhere_kind != "unknown":
        inferred_family = record.anywhere_kind
    else:
        inferred_family = record.declared_kind

    if inferred_family in ISOBMFF_FAMILIES:
        label = "isobmff_signature_away_from_byte0" if record.byte0_kind == "unknown" and record.anywhere_kind in ISOBMFF_FAMILIES else "isobmff_container_candidate"
        return Classification(family=inferred_family, label=label, confidence=0.82 if "away" in label else 0.72, evidence=evidence)

    if inferred_family in {"mkv", "webm"}:
        label = "ebml_signature_away_from_byte0" if record.byte0_kind == "unknown" and record.anywhere_kind in {"mkv", "webm"} else "ebml_container_candidate"
        return Classification(family=inferred_family, label=label, confidence=0.8 if "away" in label else 0.7, evidence=evidence)

    if inferred_family == "avi":
        label = "riff_avi_signature_away_from_byte0" if record.byte0_kind == "unknown" and record.anywhere_kind == "avi" else "riff_avi_candidate"
        return Classification(family="avi", label=label, confidence=0.79 if "away" in label else 0.69, evidence=evidence)

    if inferred_family == "mpegts":
        label = "mpegts_desync_or_partial_packets" if record.byte0_kind != "mpegts" else "mpegts_candidate"
        return Classification(family="mpegts", label=label, confidence=0.86 if "desync" in label else 0.75, evidence=evidence)

    if inferred_family in {"mpegps", "flv", "asf", "wmv"}:
        return Classification(family=inferred_family, label=f"{inferred_family}_container_candidate", confidence=0.7, evidence=evidence)

    if inferred_family in {"png", "gif", "bmp", "tiff", "webp", "heif", "avif", "jp2", "raw"}:
        return Classification(family=inferred_family, label=f"{inferred_family}_detected_candidate", confidence=0.65, evidence=evidence)

    if inferred_family in {*AUDIO_KINDS, *ARCHIVE_KINDS, *DOCUMENT_KINDS, "text"}:
        confidence = 0.9 if record.byte0_kind == inferred_family else 0.7
        return Classification(family=inferred_family, label=f"{inferred_family}_signature_candidate", confidence=confidence, evidence=evidence)

    if record.declared_kind:
        return Classification(family=record.declared_kind, label=f"{record.declared_kind}_declared_only", confidence=0.55, evidence=evidence)

    return Classification(family="unknown", label="unknown_low_signal", confidence=0.2, evidence=evidence)
