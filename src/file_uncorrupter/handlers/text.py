from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from ..atomic import AtomicArtifactWriter
from ..types import Artifact, CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome, SourceSliceSpec
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal


_TEXT_EXTENSIONS = (".txt", ".md", ".markdown", ".log", ".csv", ".json", ".xml", ".html", ".htm")


@dataclass(slots=True)
class TextRecovery:
    encoding: str
    confidence: float
    text: str
    recovered_bytes: bytes
    spans: list[dict[str, Any]]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    normalized_bytes: bytes | None = None


def _encoding(data: bytes) -> tuple[str, str, int, float]:
    for marker, label, codec in (
        (b"\x00\x00\xfe\xff", "utf-32-be", "utf-32-be"),
        (b"\xff\xfe\x00\x00", "utf-32-le", "utf-32-le"),
        (b"\xef\xbb\xbf", "utf-8-sig", "utf-8"),
        (b"\xfe\xff", "utf-16-be", "utf-16-be"),
        (b"\xff\xfe", "utf-16-le", "utf-16-le"),
    ):
        if data.startswith(marker):
            return label, codec, len(marker), 1.0
    try:
        data.decode("utf-8", errors="strict")
        return "utf-8", "utf-8", 0, 0.99 if any(byte >= 0x80 for byte in data) else 0.9
    except UnicodeDecodeError:
        pass
    valid_utf8_bytes = 0
    multibyte_sequences = 0
    cursor = 0
    while cursor < len(data):
        first = data[cursor]
        width = 1 if first < 0x80 else 2 if 0xC2 <= first <= 0xDF else 3 if 0xE0 <= first <= 0xEF else 4 if 0xF0 <= first <= 0xF4 else 1
        chunk = data[cursor:cursor + width]
        try:
            chunk.decode("utf-8", errors="strict")
            if len(chunk) == width:
                valid_utf8_bytes += width
                multibyte_sequences += int(width > 1)
                cursor += width
                continue
        except UnicodeDecodeError:
            pass
        cursor += 1
    if multibyte_sequences and valid_utf8_bytes / max(1, len(data)) >= 0.8:
        return "utf-8", "utf-8", 0, 0.78
    sample = data[:8192]
    if len(sample) >= 8:
        zero_mod4 = [sum(1 for index, byte in enumerate(sample) if index % 4 == slot and byte == 0) for slot in range(4)]
        threshold4 = len(sample) // 8
        if sum(value >= threshold4 for value in zero_mod4) >= 3:
            codec = "utf-32-be" if zero_mod4[0] > zero_mod4[3] else "utf-32-le"
            return codec, codec, 0, 0.8
        even_zero = sum(1 for index, byte in enumerate(sample) if index % 2 == 0 and byte == 0)
        odd_zero = sum(1 for index, byte in enumerate(sample) if index % 2 == 1 and byte == 0)
        if max(even_zero, odd_zero) > len(sample) // 6:
            codec = "utf-16-be" if even_zero > odd_zero else "utf-16-le"
            return codec, codec, 0, 0.78
    if any(0x80 <= byte <= 0x9F for byte in data):
        return "windows-1252", "cp1252", 0, 0.72
    return "iso-8859-1", "latin-1", 0, 0.62


def _append_span(
    spans: list[dict[str, Any]],
    output: list[str],
    text: str,
    source_start: int,
    source_end: int,
    encoding: str,
    span_type: str,
    confidence: float,
    diagnostic: str | None = None,
) -> None:
    output_start = sum(len(item) for item in output)
    output.append(text)
    span = {
        "source_start": source_start,
        "source_end": source_end,
        "output_start": output_start,
        "output_end": output_start + len(text),
        "encoding": encoding,
        "span_type": span_type,
        "confidence": confidence,
    }
    if diagnostic:
        span["diagnostic"] = diagnostic
    if (
        spans
        and spans[-1]["span_type"] == span_type
        and spans[-1]["source_end"] == source_start
        and spans[-1]["output_end"] == output_start
        and spans[-1]["encoding"] == encoding
        and spans[-1].get("diagnostic") == diagnostic
    ):
        spans[-1]["source_end"] = source_end
        spans[-1]["output_end"] = output_start + len(text)
    else:
        spans.append(span)


def _decode_utf8(data: bytes, offset: int, label: str, confidence: float) -> tuple[str, list[dict[str, Any]]]:
    output: list[str] = []
    spans: list[dict[str, Any]] = []
    index = offset
    while index < len(data):
        first = data[index]
        if first < 0x80:
            width = 1
        elif 0xC2 <= first <= 0xDF:
            width = 2
        elif 0xE0 <= first <= 0xEF:
            width = 3
        elif 0xF0 <= first <= 0xF4:
            width = 4
        else:
            width = 1
        chunk = data[index:index + width]
        try:
            text = chunk.decode("utf-8", errors="strict")
            valid = len(chunk) == width
        except UnicodeDecodeError:
            text = "\ufffd"
            valid = False
        if valid and text and (ord(text[0]) >= 32 or text in {"\t", "\n", "\r"}):
            _append_span(spans, output, text, index, index + width, label, "exact", confidence)
            index += width
        else:
            kind = "skipped_binary" if first == 0 or (first < 32 and first not in {9, 10, 13}) else "replacement"
            _append_span(spans, output, "\ufffd", index, index + 1, label, kind, 0.0, "undecodable_or_binary_byte")
            index += 1
    return "".join(output), spans


def _decode_single_byte(data: bytes, codec: str, label: str, confidence: float) -> tuple[str, list[dict[str, Any]]]:
    output: list[str] = []
    spans: list[dict[str, Any]] = []
    for index, byte in enumerate(data):
        try:
            character = bytes([byte]).decode(codec)
            valid = True
        except UnicodeDecodeError:
            character = "\ufffd"
            valid = False
        binary = byte == 0 or (byte < 32 and byte not in {9, 10, 13})
        if binary:
            _append_span(spans, output, "\ufffd", index, index + 1, label, "skipped_binary", 0.0, "binary_control_byte")
        elif valid:
            _append_span(spans, output, character, index, index + 1, label, "exact", confidence)
        else:
            _append_span(spans, output, character, index, index + 1, label, "replacement", 0.0, "undefined_codepoint")
    return "".join(output), spans


class _HTMLDiagnostics(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags = 0
        self.scripts = 0
        self.links = 0
        self.active_attributes = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags += 1
        if tag.lower() in {"script", "iframe", "object", "embed"}:
            self.scripts += 1
        for name, _ in attrs:
            if name.lower() == "href":
                self.links += 1
            if name.lower().startswith("on"):
                self.active_attributes += 1


def _structured_diagnostics(text: str, suffix: str) -> dict[str, Any]:
    suffix = suffix.lower()
    if suffix == ".json":
        try:
            value = json.loads(text)
            return {"json": {"valid": True, "root_type": type(value).__name__}}
        except json.JSONDecodeError as exc:
            return {"json": {"valid": False, "message": exc.msg, "line": exc.lineno, "column": exc.colno, "position": exc.pos}}
    if suffix == ".xml":
        try:
            root = ET.fromstring(text)
            return {"xml": {"valid": True, "root_tag": root.tag}}
        except ET.ParseError as exc:
            return {"xml": {"valid": False, "message": str(exc), "position": list(getattr(exc, "position", (0, 0)))}}
    if suffix == ".csv":
        sample = text[:65536]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(io.StringIO(sample), dialect))[:1000]
        widths = [len(row) for row in rows]
        return {"csv": {"valid": bool(rows), "delimiter": dialect.delimiter, "rows_inspected": len(rows), "row_widths": widths[:50], "consistent": len(set(widths)) <= 1}}
    if suffix in {".html", ".htm"}:
        parser = _HTMLDiagnostics()
        parser.feed(text[:1_000_000])
        return {"html": {"tags": parser.tags, "links": parser.links, "active_elements": parser.scripts, "active_attributes": parser.active_attributes}}
    if suffix in {".md", ".markdown"}:
        lines = text.splitlines()
        fences = [line for line in lines if re.match(r"^\s*(```|~~~)", line)]
        return {"markdown": {"headings": sum(1 for line in lines if re.match(r"^#{1,6}\s+", line)), "links": len(re.findall(r"\[[^\]]+\]\([^)]+\)", text)), "fences": len(fences), "fences_balanced": len(fences) % 2 == 0}}
    return {"text": {"line_count": text.count("\n") + (1 if text else 0)}}


def _structured_content_is_invalid(diagnostics: dict[str, Any]) -> bool:
    if "json" in diagnostics or "xml" in diagnostics:
        record = diagnostics.get("json", diagnostics.get("xml", {}))
        return record.get("valid") is False
    if "csv" in diagnostics:
        record = diagnostics["csv"]
        return record.get("valid") is False or record.get("consistent") is False
    if "markdown" in diagnostics:
        return diagnostics["markdown"].get("fences_balanced") is False
    return False


class TextHandler(FormatHandler):
    handler_id = "text-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        return (
            CapabilityRecord(
                family="text",
                variants=("txt", "markdown", "log", "csv", "json", "xml", "html"),
                extensions=_TEXT_EXTENSIONS,
                signatures=("bom:utf8", "bom:utf16", "bom:utf32", "bounded-text-confidence"),
                operations={"detect": "validated", "inspect": "validated", "validate": "baseline", "repair": "partial", "normalize": "validated", "extract": "validated", "preview": "baseline", "carve": "partial"},
                tools={"required": (), "optional": ()},
                limits={"max_materialized_bytes": 256 * (1 << 20)},
                encryption="not_applicable",
                active_content="HTML active content is reported and never executed.",
                outputs=({"kind": "extracted", "media_type": "text/plain"}, {"kind": "normalized", "media_type": "text/plain; charset=utf-8"}, {"kind": "diagnostics", "media_type": "application/json"}),
                fidelity="Recovered bytes remain unchanged; decoded text maps emitted characters and replacements to source byte ranges.",
                fixtures=("text-encoding-matrix", "text-invalid-spans", "structured-truncation"),
                handler_id=self.handler_id,
            ),
        )

    def recover_bytes(self, data: bytes, *, suffix: str = ".txt", normalize: bool = False) -> TextRecovery:
        label, codec, bom_length, confidence = _encoding(data)
        if codec == "utf-8":
            text, spans = _decode_utf8(data, bom_length, label, confidence)
        elif codec in {"cp1252", "latin-1"}:
            text, spans = _decode_single_byte(data, codec, label, confidence)
        else:
            payload = data[bom_length:]
            try:
                text = payload.decode(codec, errors="strict")
                span_type = "exact"
                span_confidence = confidence
            except UnicodeDecodeError:
                text = payload.decode(codec, errors="replace")
                span_type = "replacement"
                span_confidence = 0.4
            spans = [{"source_start": bom_length, "source_end": len(data), "output_start": 0, "output_end": len(text), "encoding": label, "span_type": span_type, "confidence": span_confidence}]
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8") if normalize else None
        return TextRecovery(label, confidence, text, data, spans, _structured_diagnostics(text, suffix), normalized)

    def inspect(self, context: HandlerContext) -> InspectionResult:
        data = context.source.slice(0, min(context.source.size, context.limits.max_materialized_bytes)).materialize()
        result = self.recover_bytes(data, suffix=context.record.path.suffix)
        return InspectionResult("text", True, result.confidence, diagnostics=[result.diagnostics], risk_flags=[])

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        if goal not in {RecoveryGoal.REPAIR, RecoveryGoal.NORMALIZE, RecoveryGoal.EXTRACT, RecoveryGoal.PREVIEW, RecoveryGoal.CARVE}:
            return []
        return [CandidatePlan(f"{self.handler_id}:{goal.value}", self.handler_id, goal.value, "text", goal.value, 100, (SourceSliceSpec(0, context.source.size),), estimated_materialized_bytes=context.source.size, estimated_output_bytes=context.source.size)]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        data = plan.materialize(context.source, max_bytes=context.limits.max_materialized_bytes)
        result = self.recover_bytes(data, suffix=context.record.path.suffix, normalize=plan.goal == RecoveryGoal.NORMALIZE.value)
        artifacts: list[Artifact] = []
        lossy = any(span["span_type"] in {"replacement", "skipped_binary"} for span in result.spans)
        structurally_invalid = _structured_content_is_invalid(result.diagnostics)
        partial = lossy or structurally_invalid
        if plan.goal == RecoveryGoal.NORMALIZE.value:
            grade = OutcomeGrade.PARTIAL_CONTENT.value if partial else OutcomeGrade.VALIDATED_NORMALIZED.value
        elif plan.goal == RecoveryGoal.PREVIEW.value:
            grade = OutcomeGrade.PREVIEW_ONLY.value
        else:
            grade = OutcomeGrade.PARTIAL_CONTENT.value if partial else OutcomeGrade.VALIDATED_ORIGINAL.value
        if context.output_root is not None:
            writer = AtomicArtifactWriter(context.output_root, budget=context.budget)
            payloads = [
                ("span-map.json", (json.dumps(result.spans, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"), "diagnostics", "application/json", "partial_content"),
                ("diagnostics.json", (json.dumps(result.diagnostics, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"), "diagnostics", "application/json", "partial_content"),
            ]
            if plan.goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.NORMALIZE.value}:
                payloads.append((f"recovered{context.record.path.suffix or '.txt'}", result.recovered_bytes, "repaired", "application/octet-stream", grade))
            if plan.goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}:
                payloads.append(("decoded.txt", result.text.encode("utf-8"), "extracted", "text/plain; charset=utf-8", grade))
            if plan.goal == RecoveryGoal.PREVIEW.value:
                payloads.append(("preview.txt", result.text.encode("utf-8"), "preview", "text/plain; charset=utf-8", OutcomeGrade.PREVIEW_ONLY.value))
            if result.normalized_bytes is not None and plan.goal == RecoveryGoal.NORMALIZE.value:
                payloads.append(("normalized.txt", result.normalized_bytes, "normalized", "text/plain; charset=utf-8", "validated_normalized"))
            for name, payload, kind, media_type, fidelity in payloads:
                published = writer.publish_bytes(name, payload)
                artifacts.append(Artifact(kind, published.path, published.sha256, self.handler_id, size=published.size, media_type=media_type, fidelity_grade=fidelity, validation_state="handler_validated", published=True, meta={"atomic": published.atomic}))
        return RecoveryOutcome(None, DecodeResult(ok=True, decoder=self.handler_id, decoded_format=result.encoding, telemetry={"spans": result.spans, "diagnostics": result.diagnostics, "normalized": result.normalized_bytes is not None, "lossy": lossy, "structurally_invalid": structurally_invalid}), artifacts=artifacts, grade=grade, diagnostics=[result.diagnostics])
