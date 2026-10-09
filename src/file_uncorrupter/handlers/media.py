from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..atomic import AtomicArtifactWriter
from ..budgets import BudgetTracker
from ..byte_source import FileByteSource
from ..cancellation import CancellationToken
from ..decoders import (
    ffmpeg_available,
    ffprobe_available,
    probe_video_with_ffmpeg,
    recover_media_goal_with_ffmpeg,
)
from ..types import CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal


_ASF_GUID = bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")
_SUFFIX_FAMILY = {
    ".mp4": "mp4", ".m4v": "mp4", ".mov": "mov", ".mkv": "mkv", ".webm": "webm",
    ".avi": "avi", ".ts": "mpegts", ".mts": "mpegts", ".m2ts": "mpegts", ".mpg": "mpegps", ".mpeg": "mpegps",
    ".flv": "flv", ".asf": "asf", ".wmv": "wmv", ".wav": "wav", ".mp3": "mp3", ".flac": "flac",
    ".aac": "aac", ".ogg": "ogg", ".oga": "ogg",
}


@dataclass(slots=True)
class MediaRecovery:
    family: str
    outcome: str
    prefix_bytes: int = 0
    rebuilt_bytes: bytes | None = None
    structures: dict[str, Any] = field(default_factory=dict)
    streams: list[dict[str, Any]] = field(default_factory=list)
    artifact_path: Path | None = None
    tool_evidence: dict[str, Any] = field(default_factory=dict)


def _ts_offset(data: bytes) -> int | None:
    for offset in range(min(188, len(data))):
        if sum(1 for index in range(offset, min(len(data), offset + 188 * 8), 188) if data[index] == 0x47) >= 4:
            return offset
    return None


def _detect_family(data: bytes, suffix: str) -> tuple[str, int]:
    ftyp = data.find(b"ftyp")
    if ftyp >= 4:
        brand = data[ftyp + 4:ftyp + 8]
        return ("mov" if brand == b"qt  " else "mp4"), ftyp - 4
    ebml = data.find(b"\x1a\x45\xdf\xa3")
    if ebml >= 0:
        return ("webm" if b"webm" in data[ebml:ebml + 256].lower() or suffix.lower() == ".webm" else "mkv"), ebml
    riff = data.find(b"RIFF")
    if riff >= 0 and riff + 12 <= len(data):
        kind = data[riff + 8:riff + 12]
        if kind == b"AVI ":
            return "avi", riff
        if kind == b"WAVE":
            return "wav", riff
    flv = data.find(b"FLV")
    if flv >= 0:
        return "flv", flv
    asf = data.find(_ASF_GUID)
    if asf >= 0:
        return ("wmv" if suffix.lower() == ".wmv" else "asf"), asf
    ts = _ts_offset(data)
    if ts is not None:
        return "mpegts", ts
    ps = data.find(b"\x00\x00\x01\xba")
    if ps >= 0:
        return "mpegps", ps
    if data.startswith(b"fLaC"):
        return "flac", 0
    if data.startswith(b"OggS"):
        return "ogg", 0
    if data.startswith(b"ID3") or data.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        return "mp3", 0
    if len(data) >= 2 and data[0] == 0xFF and data[1] & 0xF6 == 0xF0:
        return "aac", 0
    return _SUFFIX_FAMILY.get(suffix.lower(), "unknown"), 0


def _mp4_boxes(data: bytes) -> dict[str, Any]:
    boxes: list[dict[str, Any]] = []
    cursor = 0
    truncated = False
    while cursor + 8 <= len(data) and len(boxes) < 100_000:
        size = int.from_bytes(data[cursor:cursor + 4], "big")
        kind_bytes = data[cursor + 4:cursor + 8]
        header = 8
        if size == 1:
            if cursor + 16 > len(data):
                truncated = True
                break
            size = int.from_bytes(data[cursor + 8:cursor + 16], "big")
            header = 16
        elif size == 0:
            size = len(data) - cursor
        if size < header or cursor + size > len(data):
            truncated = True
            break
        boxes.append({"type": kind_bytes.decode("latin-1", errors="replace"), "offset": cursor, "size": size})
        cursor += size
    return {"boxes": boxes, "truncated_box": truncated, "unparsed_tail": len(data) - cursor}


def _ts_evidence(data: bytes) -> dict[str, Any]:
    packets = len(data) // 188
    continuity: dict[int, int] = {}
    discontinuities = 0
    pids: set[int] = set()
    for index in range(packets):
        packet = data[index * 188:(index + 1) * 188]
        if len(packet) != 188 or packet[0] != 0x47:
            continue
        pid = ((packet[1] & 0x1F) << 8) | packet[2]
        counter = packet[3] & 0x0F
        has_payload = packet[3] & 0x10
        pids.add(pid)
        if has_payload and pid in continuity and counter != (continuity[pid] + 1) % 16:
            discontinuities += 1
        if has_payload:
            continuity[pid] = counter
    return {"packets": packets, "trailing_bytes": len(data) % 188, "pids": sorted(pids), "continuity_discontinuities": discontinuities}


def _mp4_boxes_source(source: FileByteSource, start: int) -> dict[str, Any]:
    boxes: list[dict[str, Any]] = []
    cursor = start
    truncated = False
    while cursor + 8 <= source.size and len(boxes) < 100_000:
        header = source.read(cursor, 8)
        size = int.from_bytes(header[:4], "big")
        kind_bytes = header[4:8]
        header_size = 8
        if size == 1:
            if cursor + 16 > source.size:
                truncated = True
                break
            size = int.from_bytes(source.read(cursor + 8, 8), "big")
            header_size = 16
        elif size == 0:
            size = source.size - cursor
        if size < header_size or cursor + size > source.size:
            truncated = True
            break
        boxes.append({"type": kind_bytes.decode("latin-1", errors="replace"), "offset": cursor - start, "size": size})
        cursor += size
    return {
        "boxes": boxes,
        "truncated_box": truncated,
        "unparsed_tail": source.size - cursor,
        "source_mode": "random_access_stream",
    }


def _ts_evidence_source(source: FileByteSource, start: int) -> dict[str, Any]:
    continuity: dict[int, int] = {}
    discontinuities = 0
    pids: set[int] = set()
    packets = 0
    buffer = b""
    for chunk in source.iter_chunks(start=start):
        buffer += chunk
        complete = len(buffer) // 188
        for index in range(complete):
            packet = buffer[index * 188:(index + 1) * 188]
            if packet[0] != 0x47:
                continue
            packets += 1
            pid = ((packet[1] & 0x1F) << 8) | packet[2]
            counter = packet[3] & 0x0F
            has_payload = packet[3] & 0x10
            pids.add(pid)
            if has_payload and pid in continuity and counter != (continuity[pid] + 1) % 16:
                discontinuities += 1
            if has_payload:
                continuity[pid] = counter
        buffer = buffer[complete * 188:]
    return {
        "packets": packets,
        "trailing_bytes": len(buffer),
        "pids": sorted(pids),
        "continuity_discontinuities": discontinuities,
        "source_mode": "stream",
    }


def _count_markers_source(source: FileByteSource, start: int, markers: tuple[bytes, ...]) -> dict[bytes, int]:
    counts = {marker: 0 for marker in markers}
    overlap = max(len(marker) for marker in markers) - 1
    carry = b""
    absolute = start
    for chunk in source.iter_chunks(start=start):
        window = carry + chunk
        base = absolute - len(carry)
        for marker in markers:
            for match in re.finditer(re.escape(marker), window):
                if base + match.end() > absolute:
                    counts[marker] += 1
        carry = window[-overlap:] if overlap else b""
        absolute += len(chunk)
    return counts


def _patched_media_chunks(source: FileByteSource, start: int, family: str):
    if family in {"avi", "wav"} and source.size - start >= 12:
        header = bytearray(source.read(start, 12))
        header[4:8] = (source.size - start - 8).to_bytes(4, "little")
        yield bytes(header)
        yield from source.iter_chunks(start=start + 12)
        return
    yield from source.iter_chunks(start=start)


class MediaHandler(FormatHandler):
    handler_id = "media-structural-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        tool_goals_available = ffmpeg_available() and ffprobe_available()
        operations = {
            "detect": "validated",
            "inspect": "validated",
            "validate": "baseline",
            "repair": "partial",
            "normalize": "baseline" if tool_goals_available else "none",
            "extract": "partial" if tool_goals_available else "none",
            "preview": "partial" if tool_goals_available else "none",
            "carve": "partial",
        }
        outputs: list[dict[str, str]] = [
            {"kind": "repaired", "media_type": "application/octet-stream"},
            {"kind": "diagnostics", "media_type": "application/json"},
        ]
        if tool_goals_available:
            outputs.extend(
                [
                    {"kind": "normalized", "media_type": "video/x-matroska or audio/x-matroska"},
                    {"kind": "extracted", "media_type": "Matroska single-stream output"},
                    {"kind": "preview", "media_type": "image/png"},
                ]
            )
        return (
            CapabilityRecord(
                family="media",
                variants=("mp4", "mov", "mkv", "webm", "avi", "mpegts", "mpegps", "flv", "asf", "wmv", "wav", "mp3", "flac", "aac", "ogg"),
                extensions=tuple(sorted(_SUFFIX_FAMILY)),
                signatures=("ISOBMFF-box", "EBML", "RIFF-AVI/WAVE", "MPEG-TS/PS", "FLV", "ASF-GUID", "ID3/frame-sync", "FLAC", "ADTS", "OggS"),
                operations=operations,
                tools={"required": (), "optional": ("ffmpeg", "ffprobe")},
                limits={"max_materialized_bytes": 256 * (1 << 20), "max_decoder_seconds": 30, "max_tool_output_bytes": 1 << 20},
                encryption="Encrypted tracks/containers are reported when tools expose them; keys are not bypassed.",
                active_content="Container metadata is inert and never executed.",
                outputs=tuple(outputs),
                fidelity=(
                    "Native evidence covers container boundaries and continuity. With FFmpeg and ffprobe present, "
                    "normalization remuxes without transcoding, extraction publishes independently validated streams, "
                    "and preview publishes one decoder-validated video frame."
                    if tool_goals_available
                    else "Native evidence covers container boundaries and continuity. Normalize, stream extraction, "
                    "and preview are explicitly unavailable because FFmpeg and ffprobe are not both available."
                ),
                fixtures=("mp4-boxes", "ebml-prefix", "riff-size", "mpegts-continuity", "audio-headers", "tool-absent", "ffmpeg-goals"),
                handler_id=self.handler_id,
            ),
        )

    def recover_bytes(
        self,
        data: bytes,
        *,
        suffix: str,
        output_root: Path | None = None,
        request_tool_validation: bool = False,
        budget: BudgetTracker | None = None,
        cancellation: CancellationToken | None = None,
    ) -> MediaRecovery:
        family, prefix = _detect_family(data, suffix)
        payload = data[prefix:] if prefix else data
        structures: dict[str, Any] = {}
        rebuilt: bytes | None = payload if prefix else None
        structurally_valid = False
        if family in {"mp4", "mov"}:
            structures = _mp4_boxes(payload)
            structurally_valid = bool(structures["boxes"]) and not structures["truncated_box"]
        elif family in {"mkv", "webm"}:
            structures = {"ebml_header": payload.startswith(b"\x1a\x45\xdf\xa3"), "segment_marker": payload.find(b"\x18\x53\x80\x67")}
            structurally_valid = bool(structures["ebml_header"])
        elif family in {"avi", "wav"}:
            observed = len(payload) - 8
            declared = int.from_bytes(payload[4:8], "little") if len(payload) >= 8 else -1
            structures = {"declared_riff_size": declared, "observed_riff_size": observed, "form": payload[8:12].decode("latin-1", errors="replace")}
            structurally_valid = len(payload) >= 12
            if structurally_valid and declared != observed:
                candidate = bytearray(payload)
                candidate[4:8] = observed.to_bytes(4, "little")
                rebuilt = bytes(candidate)
        elif family == "mpegts":
            structures = _ts_evidence(payload)
            structurally_valid = structures["packets"] >= 4
        elif family == "mpegps":
            structures = {"pack_headers": payload.count(b"\x00\x00\x01\xba"), "stream_starts": payload.count(b"\x00\x00\x01")}
            structurally_valid = structures["pack_headers"] > 0
        elif family == "flv":
            structures = {"version": payload[3] if len(payload) > 3 else None, "flags": payload[4] if len(payload) > 4 else None, "data_offset": int.from_bytes(payload[5:9], "big") if len(payload) >= 9 else None}
            structurally_valid = payload.startswith(b"FLV") and len(payload) >= 9
        elif family in {"asf", "wmv"}:
            structures = {"asf_header_guid": payload.startswith(_ASF_GUID)}
            structurally_valid = bool(structures["asf_header_guid"])
        elif family == "mp3":
            structures = {"id3": payload.startswith(b"ID3"), "frame_syncs": sum(payload.count(prefix) for prefix in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))}
            structurally_valid = structures["id3"] or structures["frame_syncs"] > 0
        elif family == "flac":
            structures = {"flac_marker": payload.startswith(b"fLaC")}
            structurally_valid = bool(structures["flac_marker"])
        elif family == "aac":
            structures = {"adts_sync": len(payload) >= 2 and payload[0] == 0xFF and payload[1] & 0xF6 == 0xF0}
            structurally_valid = bool(structures["adts_sync"])
        elif family == "ogg":
            structures = {"pages": payload.count(b"OggS")}
            structurally_valid = structures["pages"] > 0

        if structurally_valid and rebuilt is not None:
            outcome = "repaired"
        elif structurally_valid:
            outcome = "validated_original"
        elif structures:
            outcome = "partial_content"
        else:
            outcome = "failed"
        artifact = None
        if output_root is not None and rebuilt is not None:
            extension = Path(suffix).suffix or ".bin"
            artifact = AtomicArtifactWriter(output_root, budget=budget).publish_bytes(f"repaired{extension}", rebuilt).path
        tool: dict[str, Any] = {}
        streams: list[dict[str, Any]] = []
        if request_tool_validation:
            available = ffmpeg_available() and ffprobe_available()
            if not available:
                tool = {"available": False, "error": "ffmpeg_or_ffprobe_not_found_or_disabled"}
            else:
                probe = probe_video_with_ffmpeg(rebuilt or data, family, cancellation=cancellation)
                tool = {"available": True, "ok": probe.ok, "error": probe.error, "decoder": probe.decoder, "duration_ms": probe.duration_ms, "frame_count": probe.frame_count}
                raw_streams = probe.telemetry.get("streams", []) if isinstance(probe.telemetry, dict) else []
                streams = [{"index": item.get("index"), "type": item.get("codec_type"), "codec": item.get("codec_name"), "width": item.get("width"), "height": item.get("height"), "duration": item.get("duration"), "frames": item.get("nb_frames")} for item in raw_streams]
        return MediaRecovery(family, outcome, prefix, rebuilt, structures, streams, artifact, tool)

    def recover_source(
        self,
        source: FileByteSource,
        *,
        suffix: str,
        output_root: Path | None = None,
        budget: BudgetTracker | None = None,
        goal: str | None = None,
    ) -> MediaRecovery:
        """Inspect native container structure without whole-file materialization."""
        sample = source.prefix(min(source.size, 4 * (1 << 20)))
        family, prefix = _detect_family(sample, suffix)
        start = min(prefix, source.size)
        payload_size = source.size - start
        structures: dict[str, Any]
        structurally_valid = False
        rebuilt_needed = start > 0

        if family in {"mp4", "mov"}:
            structures = _mp4_boxes_source(source, start)
            structurally_valid = bool(structures["boxes"]) and not structures["truncated_box"]
        elif family in {"mkv", "webm"}:
            header = source.read(start, min(4096, payload_size)) if payload_size else b""
            structures = {
                "ebml_header": header.startswith(b"\x1a\x45\xdf\xa3"),
                "segment_marker": header.find(b"\x18\x53\x80\x67"),
                "source_mode": "bounded_header",
            }
            structurally_valid = bool(structures["ebml_header"])
        elif family in {"avi", "wav"}:
            header = source.read(start, min(12, payload_size)) if payload_size else b""
            observed = payload_size - 8
            declared = int.from_bytes(header[4:8], "little") if len(header) >= 8 else -1
            structures = {
                "declared_riff_size": declared,
                "observed_riff_size": observed,
                "form": header[8:12].decode("latin-1", errors="replace"),
                "source_mode": "bounded_header",
            }
            structurally_valid = len(header) >= 12
            rebuilt_needed = rebuilt_needed or (structurally_valid and declared != observed)
        elif family == "mpegts":
            structures = _ts_evidence_source(source, start)
            structurally_valid = structures["packets"] >= 4
        elif family == "mpegps":
            counts = _count_markers_source(source, start, (b"\x00\x00\x01\xba", b"\x00\x00\x01"))
            structures = {
                "pack_headers": counts[b"\x00\x00\x01\xba"],
                "stream_starts": counts[b"\x00\x00\x01"],
                "source_mode": "stream",
            }
            structurally_valid = structures["pack_headers"] > 0
        elif family == "flv":
            header = source.read(start, min(9, payload_size)) if payload_size else b""
            structures = {
                "version": header[3] if len(header) > 3 else None,
                "flags": header[4] if len(header) > 4 else None,
                "data_offset": int.from_bytes(header[5:9], "big") if len(header) >= 9 else None,
                "source_mode": "bounded_header",
            }
            structurally_valid = header.startswith(b"FLV") and len(header) >= 9
        elif family in {"asf", "wmv"}:
            header = source.read(start, min(len(_ASF_GUID), payload_size)) if payload_size else b""
            structures = {"asf_header_guid": header.startswith(_ASF_GUID), "source_mode": "bounded_header"}
            structurally_valid = bool(structures["asf_header_guid"])
        elif family == "mp3":
            header = source.read(start, min(4 * (1 << 20), payload_size)) if payload_size else b""
            structures = {
                "id3": header.startswith(b"ID3"),
                "frame_syncs_in_window": sum(header.count(marker) for marker in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")),
                "inspection_window_bytes": len(header),
            }
            structurally_valid = structures["id3"] or structures["frame_syncs_in_window"] > 0
        elif family == "flac":
            header = source.read(start, min(4, payload_size)) if payload_size else b""
            structures = {"flac_marker": header.startswith(b"fLaC"), "source_mode": "bounded_header"}
            structurally_valid = bool(structures["flac_marker"])
        elif family == "aac":
            header = source.read(start, min(2, payload_size)) if payload_size else b""
            structures = {"adts_sync": len(header) >= 2 and header[0] == 0xFF and header[1] & 0xF6 == 0xF0, "source_mode": "bounded_header"}
            structurally_valid = bool(structures["adts_sync"])
        elif family == "ogg":
            counts = _count_markers_source(source, start, (b"OggS",))
            structures = {"pages": counts[b"OggS"], "source_mode": "stream"}
            structurally_valid = structures["pages"] > 0
        else:
            structures = {"source_mode": "bounded_header", "inspection_window_bytes": len(sample)}

        artifact = None
        if output_root is not None and rebuilt_needed and goal in {None, RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value}:
            extension = Path(suffix).suffix or ".bin"
            published = AtomicArtifactWriter(output_root, budget=budget).publish_stream(
                f"repaired{extension}",
                _patched_media_chunks(source, start, family),
            )
            artifact = published.path
            structures["publication"] = {
                "sha256": published.sha256,
                "size": published.size,
                "atomic": published.atomic,
                "source_mode": "stream",
            }
        source.assert_unchanged()
        if structurally_valid and rebuilt_needed:
            outcome = "repaired"
        elif structurally_valid:
            outcome = "validated_original"
        elif structures:
            outcome = "partial_content"
        else:
            outcome = "failed"
        return MediaRecovery(family, outcome, start, None, structures, [], artifact, {})

    def inspect(self, context: HandlerContext) -> InspectionResult:
        result = self.recover_source(context.source, suffix=context.record.path.suffix)
        return InspectionResult("media", result.outcome != "failed", 0.95 if result.outcome == "validated_original" else 0.72, diagnostics=[result.structures], parts=result.streams)

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        native_goals = {RecoveryGoal.REPAIR, RecoveryGoal.CARVE}
        tool_goals = {RecoveryGoal.NORMALIZE, RecoveryGoal.EXTRACT, RecoveryGoal.PREVIEW}
        if goal not in native_goals | tool_goals:
            return []
        if goal in tool_goals and not (ffmpeg_available() and ffprobe_available()):
            return []
        return [
            CandidatePlan(
                f"{self.handler_id}:{goal.value}",
                self.handler_id,
                goal.value,
                "media",
                goal.value,
                100,
                (),
                estimated_materialized_bytes=0,
                estimated_output_bytes=context.source.size if goal is not RecoveryGoal.PREVIEW else 1 << 20,
                meta={"source_mode": "stream_or_direct_tool_path"},
            )
        ]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        if plan.goal in {RecoveryGoal.NORMALIZE.value, RecoveryGoal.EXTRACT.value, RecoveryGoal.PREVIEW.value}:
            if context.output_root is None:
                return RecoveryOutcome(
                    None,
                    DecodeResult(ok=False, decoder=self.handler_id, error="media_goal_requires_output_root"),
                    grade=OutcomeGrade.FAILED.value,
                )
            native = self.recover_source(context.source, suffix=context.record.path.suffix)
            decoded, artifacts = recover_media_goal_with_ffmpeg(
                context.source.path,
                native.family,
                context.output_root,
                plan.goal,
                budget=context.budget,
                cancellation=context.cancellation,
                timeout_seconds=context.limits.max_decoder_seconds,
                max_tool_output_bytes=context.limits.max_tool_output_bytes,
                max_tool_artifact_bytes=context.limits.max_materialized_bytes,
                max_streams=min(64, context.limits.max_artifacts),
                input_offset=native.prefix_bytes,
            )
            decoded.telemetry.setdefault("family", native.family)
            decoded.telemetry.setdefault("native_outcome", native.outcome)
            decoded.telemetry.setdefault("prefix_bytes", native.prefix_bytes)
            decoded.telemetry.setdefault("structures", native.structures)
            if decoded.ok:
                grade = str(decoded.telemetry.get("fidelity_grade") or OutcomeGrade.PARTIAL_CONTENT.value)
            elif decoded.error in {"ffmpeg_or_ffprobe_not_found", "external_tools_disabled"}:
                grade = OutcomeGrade.UNAVAILABLE_DEPENDENCY.value
            else:
                grade = OutcomeGrade.FAILED.value
            diagnostics = [native.structures]
            warnings = decoded.telemetry.get("warnings")
            if isinstance(warnings, list):
                diagnostics.extend({"warning": str(warning)} for warning in warnings)
            return RecoveryOutcome(None, decoded, artifacts=artifacts, grade=grade, diagnostics=diagnostics)

        result = self.recover_source(
            context.source,
            suffix=context.record.path.suffix,
            output_root=context.output_root,
            budget=context.budget,
            goal=plan.goal,
        )
        ok = result.outcome in {"validated_original", "repaired", "partial_content"}
        grade = OutcomeGrade.VALIDATED_ORIGINAL.value if result.outcome in {"validated_original", "repaired"} else OutcomeGrade.PARTIAL_CONTENT.value if ok else OutcomeGrade.FAILED.value
        return RecoveryOutcome(None, DecodeResult(ok=ok, decoder=self.handler_id, telemetry={"family": result.family, "outcome": result.outcome, "prefix_bytes": result.prefix_bytes, "structures": result.structures, "streams": result.streams, "tool": result.tool_evidence}), grade=grade)
