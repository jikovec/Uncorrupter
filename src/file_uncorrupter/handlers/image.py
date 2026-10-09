from __future__ import annotations

import binascii
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from ..atomic import AtomicArtifactWriter
from ..budgets import BudgetTracker
from ..byte_source import FileByteSource
from ..decoders import save_with_pillow
from ..types import CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal


_EXTENSIONS = {
    ".png": "png", ".gif": "gif", ".bmp": "bmp", ".webp": "webp",
    ".tif": "tiff", ".tiff": "tiff", ".heic": "heif", ".heif": "heif",
    ".avif": "avif", ".jp2": "jp2", ".j2k": "jp2", ".jpx": "jp2",
    ".raw": "raw", ".dng": "raw", ".nef": "raw", ".cr2": "raw", ".arw": "raw",
}

_OUTPUT_SUFFIX = {"png": ".png", "gif": ".gif", "bmp": ".bmp", "webp": ".webp", "tiff": ".tif", "heif": ".heif", "avif": ".avif", "jp2": ".jp2", "raw": ".raw"}


@dataclass(slots=True)
class ImageRecovery:
    family: str
    outcome: str
    width: int = 0
    height: int = 0
    frame_count: int = 0
    page_count: int = 0
    rebuilt_bytes: bytes | None = None
    artifact_path: Path | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _family(data: bytes, suffix: str) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in {b"avif", b"avis"}:
            return "avif"
        if brand.startswith((b"hei", b"mif")):
            return "heif"
    if data.startswith(b"\x00\x00\x00\x0cjP  \r\n\x87\n"):
        return "jp2"
    return _EXTENSIONS.get(suffix.lower(), "unknown")


def _pillow_evidence(data: Any) -> tuple[bool, int, int, int, str]:
    try:
        source = io.BytesIO(data) if isinstance(data, bytes) else data
        with Image.open(source) as image:
            frames = int(getattr(image, "n_frames", 1))
            width, height = image.size
            for index in range(frames):
                image.seek(index)
                image.load()
            return True, width, height, frames, str(image.format or "")
    except Exception as exc:
        return False, 0, 0, 0, str(exc)


def _repair_png(data: bytes) -> tuple[bytes | None, dict[str, Any]]:
    diagnostics: dict[str, Any] = {"chunks": [], "crc_repairs": 0, "iend_appended": False, "truncated_chunk": False}
    signature = b"\x89PNG\r\n\x1a\n"
    start = data.find(signature)
    if start < 0:
        return None, diagnostics
    output = bytearray(signature)
    cursor = start + 8
    saw_ihdr = False
    saw_idat = False
    saw_iend = False
    while cursor + 12 <= len(data):
        length = int.from_bytes(data[cursor:cursor + 4], "big")
        if length > 256 * (1 << 20) or cursor + 12 + length > len(data):
            diagnostics["truncated_chunk"] = True
            break
        kind = data[cursor + 4:cursor + 8]
        payload = data[cursor + 8:cursor + 8 + length]
        observed = int.from_bytes(data[cursor + 8 + length:cursor + 12 + length], "big")
        expected = binascii.crc32(kind + payload) & 0xFFFFFFFF
        if observed != expected:
            diagnostics["crc_repairs"] += 1
        output.extend(length.to_bytes(4, "big") + kind + payload + expected.to_bytes(4, "big"))
        label = kind.decode("latin-1", errors="replace")
        diagnostics["chunks"].append({"type": label, "length": length, "crc_valid": observed == expected})
        saw_ihdr = saw_ihdr or kind == b"IHDR"
        saw_idat = saw_idat or kind == b"IDAT"
        saw_iend = saw_iend or kind == b"IEND"
        cursor += 12 + length
        if kind == b"IEND":
            break
    if not saw_iend and saw_ihdr and saw_idat:
        output.extend(b"\x00\x00\x00\x00IEND\xaeB`\x82")
        diagnostics["iend_appended"] = True
    if not (saw_ihdr and saw_idat and (saw_iend or diagnostics["iend_appended"])):
        return None, diagnostics
    rebuilt = bytes(output)
    return (rebuilt if rebuilt != data else None), diagnostics


class ImageHandler(FormatHandler):
    handler_id = "image-structural-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        registered = {extension.lower() for extension in Image.registered_extensions()}
        optional_available = any(extension in registered for extension in {".avif", ".heic", ".jp2"})
        return (
            CapabilityRecord(
                family="image",
                variants=("png", "gif", "bmp", "webp", "tiff", "heif", "avif", "jp2", "raw"),
                extensions=tuple(sorted(_EXTENSIONS)),
                signatures=("PNG-chunks", "GIF-blocks", "BMP-DIB", "RIFF-WebP", "TIFF-IFD", "ISOBMFF-image", "JP2"),
                operations={"detect": "validated", "inspect": "validated", "validate": "validated", "repair": "partial", "normalize": "partial", "extract": "none", "preview": "partial" if optional_available else "baseline", "carve": "partial"},
                tools={"required": (), "optional": ("Pillow format plugins",)},
                limits={"max_materialized_bytes": 256 * (1 << 20), "max_artifacts": 1_000},
                encryption="not_applicable",
                active_content="Metadata is treated as inert; no embedded actions are executed.",
                outputs=({"kind": "repaired", "media_type": "image/*"}, {"kind": "normalized", "media_type": "image/*"}, {"kind": "preview", "media_type": "image/png"}),
                fidelity="Native repairs are limited to structurally derivable lengths, CRCs, and trailers. Animation and multipage validation is explicit; first-frame output is preview only.",
                fixtures=("png-crc", "gif-animation", "bmp-size", "webp-riff", "tiff-multipage", "optional-codec"),
                handler_id=self.handler_id,
            ),
        )

    def recover_bytes(
        self,
        data: bytes,
        *,
        suffix: str,
        output_root: Path | None = None,
        budget: BudgetTracker | None = None,
    ) -> ImageRecovery:
        family = _family(data, suffix)
        rebuilt: bytes | None = None
        diagnostics: dict[str, Any] = {}
        if family == "png":
            rebuilt, diagnostics = _repair_png(data)
        elif family == "gif":
            diagnostics = {"trailer_present": data.endswith(b";")}
            if data.startswith((b"GIF87a", b"GIF89a")) and not data.endswith(b";"):
                candidate = data + b";"
                if _pillow_evidence(candidate)[0]:
                    rebuilt = candidate
        elif family == "bmp":
            diagnostics = {"declared_size": int.from_bytes(data[2:6], "little") if len(data) >= 6 else 0, "observed_size": len(data)}
            if len(data) >= 14 and data.startswith(b"BM") and int.from_bytes(data[2:6], "little") != len(data):
                candidate = bytearray(data)
                candidate[2:6] = len(candidate).to_bytes(4, "little")
                rebuilt = bytes(candidate)
        elif family == "webp":
            diagnostics = {"declared_riff_size": int.from_bytes(data[4:8], "little") if len(data) >= 8 else 0, "expected_riff_size": max(0, len(data) - 8)}
            if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP" and int.from_bytes(data[4:8], "little") != len(data) - 8:
                candidate = bytearray(data)
                candidate[4:8] = (len(candidate) - 8).to_bytes(4, "little")
                rebuilt = bytes(candidate)
        elif family == "tiff":
            diagnostics = {"byte_order": "little" if data.startswith(b"II") else "big" if data.startswith(b"MM") else "unknown"}
        else:
            diagnostics = {"codec_dependent": True}

        candidate = rebuilt or data
        valid, width, height, frames, decoder_error = _pillow_evidence(candidate)
        diagnostics["decoder_valid"] = valid
        if decoder_error and not valid:
            diagnostics["decoder_error"] = decoder_error
        if valid and rebuilt is not None:
            outcome = "repaired"
        elif valid:
            outcome = "validated_original"
        elif family in {"heif", "avif", "jp2", "raw"}:
            outcome = "unavailable_dependency"
            rebuilt = None
        else:
            outcome = "failed"
            rebuilt = None
        artifact = None
        if output_root is not None and rebuilt is not None:
            extension = _OUTPUT_SUFFIX.get(family, Path(suffix).suffix or ".bin")
            artifact = AtomicArtifactWriter(output_root, budget=budget).publish_bytes(f"repaired{extension}", rebuilt, validator=lambda path: _pillow_evidence(path.read_bytes())[0]).path
        pages = frames if family == "tiff" else 0
        return ImageRecovery(family, outcome, width, height, frames, pages, rebuilt, artifact, diagnostics)

    def recover_source(
        self,
        source: FileByteSource,
        *,
        suffix: str,
        output_root: Path | None = None,
        budget: BudgetTracker | None = None,
        allow_native_repair: bool = False,
    ) -> ImageRecovery:
        prefix = source.prefix(min(source.size, 4096))
        family = _family(prefix, suffix)
        source.assert_unchanged()
        with source.open_reader() as reader:
            valid, width, height, frames, decoder_error = _pillow_evidence(reader)
        source.assert_unchanged()
        diagnostics: dict[str, Any] = {
            "decoder_valid": valid,
            "source_mode": "seekable_stream",
            "materialized": False,
        }
        if family == "tiff":
            diagnostics["byte_order"] = "little" if prefix.startswith(b"II") else "big" if prefix.startswith(b"MM") else "unknown"
        if decoder_error and not valid:
            diagnostics["decoder_error"] = decoder_error

        native_families = {"png", "gif", "bmp", "webp"}
        if allow_native_repair and family in native_families:
            if source.size <= source.limits.max_materialized_bytes:
                data = source.slice(0, source.size).materialize()
                result = self.recover_bytes(data, suffix=suffix, output_root=output_root, budget=budget)
                result.diagnostics.setdefault("source_mode", "bounded_materialization_fallback")
                result.diagnostics["materialized"] = True
                return result
            diagnostics["materialization_fallback"] = {
                "state": "not_run",
                "source_bytes": source.size,
                "limit": source.limits.max_materialized_bytes,
            }

        if valid:
            outcome = "validated_original"
        elif family in {"heif", "avif", "jp2", "raw"}:
            outcome = "unavailable_dependency"
        else:
            outcome = "failed"
        return ImageRecovery(
            family,
            outcome,
            width,
            height,
            frames,
            frames if family == "tiff" else 0,
            diagnostics=diagnostics,
        )

    def inspect(self, context: HandlerContext) -> InspectionResult:
        result = self.recover_source(context.source, suffix=context.record.path.suffix)
        return InspectionResult("image", result.outcome != "failed", 0.98 if result.outcome == "validated_original" else 0.75, diagnostics=[result.diagnostics], parts=[{"family": result.family, "width": result.width, "height": result.height, "frames": result.frame_count, "pages": result.page_count}])

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        if goal not in {RecoveryGoal.REPAIR, RecoveryGoal.NORMALIZE, RecoveryGoal.PREVIEW, RecoveryGoal.CARVE}:
            return []
        return [CandidatePlan(f"{self.handler_id}:{goal.value}", self.handler_id, goal.value, "image", goal.value, 100, (), estimated_materialized_bytes=0, estimated_output_bytes=context.source.size, meta={"source_mode": "seekable_stream", "fallback_materialization_limit": context.limits.max_materialized_bytes})]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        result = self.recover_source(
            context.source,
            suffix=context.record.path.suffix,
            output_root=context.output_root if plan.goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value} else None,
            budget=context.budget,
            allow_native_repair=plan.goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value},
        )
        payload: Any = result.rebuilt_bytes
        decode = DecodeResult(ok=result.outcome in {"validated_original", "repaired"}, decoder=self.handler_id, width=result.width, height=result.height, frame_count=result.frame_count)
        if plan.goal == RecoveryGoal.NORMALIZE.value:
            if result.family not in {"png", "gif", "bmp", "webp", "tiff"} or context.output_root is None:
                decode = DecodeResult(ok=False, decoder="pillow", error=f"normalization_unavailable:{result.family}")
                grade = OutcomeGrade.UNAVAILABLE_DEPENDENCY.value
            else:
                extension = _OUTPUT_SUFFIX[result.family]
                if payload is not None:
                    decode = save_with_pillow(payload, context.output_root / f"normalized{extension}", result.family, budget=context.budget)
                else:
                    with context.source.open_reader() as reader:
                        decode = save_with_pillow(reader, context.output_root / f"normalized{extension}", result.family, budget=context.budget)
                grade = OutcomeGrade.VALIDATED_NORMALIZED.value if decode.ok else OutcomeGrade.FAILED.value
        elif plan.goal == RecoveryGoal.PREVIEW.value:
            if context.output_root is None:
                decode = DecodeResult(ok=False, decoder="pillow", error="preview_output_root_required")
                grade = OutcomeGrade.FAILED.value
            else:
                if payload is not None:
                    decode = save_with_pillow(payload, context.output_root / "preview.png", "png", budget=context.budget)
                else:
                    with context.source.open_reader() as reader:
                        decode = save_with_pillow(reader, context.output_root / "preview.png", "png", budget=context.budget)
                grade = OutcomeGrade.PREVIEW_ONLY.value if decode.ok else OutcomeGrade.UNAVAILABLE_DEPENDENCY.value if result.outcome == "unavailable_dependency" else OutcomeGrade.FAILED.value
        else:
            grade = OutcomeGrade.VALIDATED_ORIGINAL.value if decode.ok else OutcomeGrade.UNAVAILABLE_DEPENDENCY.value if result.outcome == "unavailable_dependency" else OutcomeGrade.FAILED.value
        decode.telemetry.update({"family": result.family, "outcome": result.outcome, "pages": result.page_count, "diagnostics": result.diagnostics, "requested_goal": plan.goal})
        return RecoveryOutcome(None, decode, grade=grade)
