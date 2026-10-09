from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..atomic import AtomicArtifactWriter
from ..budgets import BudgetExceeded, BudgetTracker, ResourceLimits
from ..byte_source import FileByteSource
from ..paths import PathLayoutError, safe_relative_path
from ..types import CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome
from .archive import ArchiveHandler
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal


@dataclass(slots=True)
class DocumentPartResult:
    name: str
    media_type: str
    required: bool = False
    present: bool = True
    parsed: bool = False
    macro: bool = False
    active_content: bool = False
    warning: str = ""


@dataclass(slots=True)
class PackageRecovery:
    package_type: str
    outcome: str
    parts: list[DocumentPartResult] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    macro_parts: list[str] = field(default_factory=list)
    active_content: bool = False
    text: str = ""
    artifacts: list[Path] = field(default_factory=list)
    rebuilt_bytes: bytes | None = None
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


_TYPE_FROM_SUFFIX = {
    ".docx": "docx", ".docm": "docx",
    ".xlsx": "xlsx", ".xlsm": "xlsx",
    ".pptx": "pptx", ".pptm": "pptx",
    ".odt": "odt", ".ods": "ods", ".odp": "odp",
}

_REQUIRED = {
    "docx": ("[Content_Types].xml", "_rels/.rels", "word/document.xml"),
    "xlsx": ("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"),
    "pptx": ("[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"),
    "odt": ("mimetype", "META-INF/manifest.xml", "content.xml"),
    "ods": ("mimetype", "META-INF/manifest.xml", "content.xml"),
    "odp": ("mimetype", "META-INF/manifest.xml", "content.xml"),
}


def _media_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return {
        ".xml": "application/xml", ".rels": "application/vnd.openxmlformats-package.relationships+xml",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
        ".bin": "application/octet-stream",
    }.get(suffix, "application/octet-stream")


def _detect_type(names: set[str], suffix: str, members: dict[str, bytes]) -> str:
    declared = _TYPE_FROM_SUFFIX.get(suffix.lower())
    if "word/document.xml" in names:
        return "docx"
    if "xl/workbook.xml" in names:
        return "xlsx"
    if "ppt/presentation.xml" in names:
        return "pptx"
    mimetype = members.get("mimetype", b"").decode("ascii", errors="ignore")
    if "opendocument.text" in mimetype:
        return "odt"
    if "opendocument.spreadsheet" in mimetype:
        return "ods"
    if "opendocument.presentation" in mimetype:
        return "odp"
    return declared or "unknown"


def _detect_type_from_names(names: set[str], suffix: str, mimetype: str) -> str:
    if "word/document.xml" in names:
        return "docx"
    if "xl/workbook.xml" in names:
        return "xlsx"
    if "ppt/presentation.xml" in names:
        return "pptx"
    if "opendocument.text" in mimetype:
        return "odt"
    if "opendocument.spreadsheet" in mimetype:
        return "ods"
    if "opendocument.presentation" in mimetype:
        return "odp"
    return _TYPE_FROM_SUFFIX.get(suffix.lower(), "unknown")


def _iter_reader(reader: Any, chunk_size: int = 1 << 20):
    while True:
        chunk = reader.read(chunk_size)
        if not chunk:
            return
        yield chunk


def _xml_text_stream(reader: Any, *, max_text_chars: int) -> tuple[str, bool, str, bool, bool]:
    """Incrementally parse inert XML and retain only bounded textual content."""
    parser = ET.XMLPullParser(events=("start", "end"))
    text_fragments: list[str] = []
    text_length = 0
    truncated = False
    active_relationship = False
    scan_tail = b""
    try:
        for chunk in _iter_reader(reader):
            scan = (scan_tail + chunk).upper()
            if b"<!DOCTYPE" in scan or b"<!ENTITY" in scan:
                return "", False, "doctype_or_entity_rejected", False, False
            scan_tail = scan[-16:]
            parser.feed(chunk)
            for event, element in parser.read_events():
                if event == "start" and element.attrib.get("TargetMode", "").lower() == "external":
                    active_relationship = True
                if event != "end":
                    continue
                for value in (element.text, element.tail):
                    normalized = " ".join((value or "").split())
                    if not normalized:
                        continue
                    remaining = max_text_chars - text_length
                    if remaining <= 0:
                        truncated = True
                        continue
                    selected = normalized[:remaining]
                    text_fragments.append(selected)
                    text_length += len(selected)
                    truncated = truncated or len(selected) < len(normalized)
                element.clear()
        parser.close()
    except (ET.ParseError, UnicodeError) as exc:
        return " ".join(text_fragments), False, str(exc), truncated, active_relationship
    return " ".join(text_fragments), True, "", truncated, active_relationship


def _xml_text(payload: bytes) -> tuple[str, bool, str]:
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        return "", False, "doctype_or_entity_rejected"
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        decoded = payload.decode("utf-8", errors="replace")
        fragments = re.findall(r">([^<>]+)<", decoded)
        return " ".join(item.strip() for item in fragments if item.strip()), False, str(exc)
    text = " ".join(item.strip() for item in root.itertext() if item.strip())
    return text, True, ""


class PackageDocumentHandler(FormatHandler):
    handler_id = "package-document-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        return (
            CapabilityRecord(
                family="package_document",
                variants=("docx", "docm", "xlsx", "xlsm", "pptx", "pptm", "odt", "ods", "odp"),
                extensions=tuple(sorted(_TYPE_FROM_SUFFIX)),
                signatures=("zip-package", "[Content_Types].xml", "META-INF/manifest.xml", "mimetype"),
                operations={"detect": "validated", "inspect": "validated", "validate": "validated", "repair": "partial", "normalize": "none", "extract": "validated", "preview": "partial", "carve": "partial"},
                tools={"required": (), "optional": ()},
                limits={"max_archive_members": 10_000, "max_decompressed_bytes": 1 << 30, "max_nesting_depth": 3},
                encryption="Encrypted ZIP members are reported; passwords are not guessed.",
                active_content="Macros, external relationships, embedded objects, and active XML declarations are reported and never executed.",
                outputs=({"kind": "repaired", "media_type": "application/zip"}, {"kind": "extracted", "media_type": "text/plain"}, {"kind": "extracted", "media_type": "application/octet-stream"}),
                fidelity="Full-package status requires every required part and parseable package metadata; otherwise extracted parts are partial content.",
                fixtures=("package-matrix", "package-missing-part", "package-macro", "package-local-rebuild"),
                handler_id=self.handler_id,
            ),
        )

    def recover_bytes(
        self,
        data: bytes,
        *,
        suffix: str,
        output_root: Path | None = None,
        limits: ResourceLimits | None = None,
        budget: BudgetTracker | None = None,
        goal: str | None = None,
    ) -> PackageRecovery:
        limits = limits or ResourceLimits()
        rebuilt: bytes | None = None
        repaired = False
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
            infos = archive.infolist()
        except zipfile.BadZipFile:
            archive_result = ArchiveHandler().recover_bytes(data, suffix=".zip", limits=limits)
            if archive_result.rebuilt_bytes is None:
                return PackageRecovery(_TYPE_FROM_SUFFIX.get(suffix.lower(), "unknown"), "failed", diagnostics=archive_result.diagnostics)
            rebuilt = archive_result.rebuilt_bytes
            repaired = True
            archive = zipfile.ZipFile(io.BytesIO(rebuilt))
            infos = archive.infolist()

        members: dict[str, bytes] = {}
        diagnostics: list[dict[str, Any]] = []
        total = 0
        for index, info in enumerate(sorted(infos, key=lambda item: item.filename.casefold())):
            if index >= limits.max_archive_members:
                diagnostics.append({"budget": "archive_members", "member": info.filename})
                break
            if info.flag_bits & 1:
                diagnostics.append({"encrypted": info.filename})
                continue
            try:
                safe = safe_relative_path(info.filename).as_posix()
            except PathLayoutError:
                diagnostics.append({"unsafe_path": info.filename})
                continue
            if info.is_dir():
                continue
            if info.file_size > limits.max_archive_member_bytes or total + info.file_size > limits.max_decompressed_bytes:
                diagnostics.append({"budget": "decompressed_bytes", "member": info.filename})
                continue
            try:
                payload = archive.read(info)
            except (RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
                diagnostics.append({"unreadable": info.filename, "error": str(exc)})
                continue
            members[safe] = payload
            total += len(payload)
        archive.close()

        names = set(members)
        package_type = _detect_type(names, suffix, members)
        required = list(_REQUIRED.get(package_type, ()))
        missing = [name for name in required if name not in names]
        parts: list[DocumentPartResult] = []
        macro_parts: list[str] = []
        active = False
        text_fragments: list[str] = []
        artifacts: list[Path] = []
        writer = AtomicArtifactWriter(output_root, budget=budget) if output_root is not None else None
        publish_parts = goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}
        publish_text = goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.PREVIEW.value, RecoveryGoal.CARVE.value}
        publish_repair = goal is None or goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value}

        for name, payload in sorted(members.items()):
            macro = name.lower().endswith("vbaproject.bin") or "macros/" in name.lower()
            is_active = macro or "/embeddings/" in name.lower()
            part = DocumentPartResult(name, _media_type(name), name in required, macro=macro, active_content=is_active)
            if macro:
                macro_parts.append(name)
            active = active or is_active
            if name.lower().endswith((".xml", ".rels")):
                extracted, parsed, warning = _xml_text(payload)
                part.parsed = parsed
                part.warning = warning
                if extracted and not name.endswith("[Content_Types].xml") and not name.endswith(".rels"):
                    text_fragments.append(extracted)
                if name.endswith(".rels"):
                    try:
                        root = ET.fromstring(payload)
                        if any(element.attrib.get("TargetMode", "").lower() == "external" for element in root.iter()):
                            part.active_content = True
                            active = True
                    except ET.ParseError:
                        pass
            parts.append(part)
            if writer is not None and publish_parts and ("/media/" in name.lower() or "/embeddings/" in name.lower() or name.startswith("Pictures/")):
                try:
                    artifacts.append(writer.publish_bytes(Path("parts") / safe_relative_path(name), payload).path)
                except BudgetExceeded:
                    raise
                except Exception as exc:
                    diagnostics.append({"publication_failed": name, "error": str(exc)})

        text = "\n".join(dict.fromkeys(fragment for fragment in text_fragments if fragment))
        if writer is not None and text and publish_text:
            text_name = "preview.txt" if goal == RecoveryGoal.PREVIEW.value else "extracted-text.txt"
            artifacts.append(writer.publish_bytes(text_name, (text + "\n").encode("utf-8")).path)
        if writer is not None and rebuilt is not None and publish_repair:
            extension = suffix.lower() if suffix.lower() in _TYPE_FROM_SUFFIX else ".zip"
            artifacts.append(writer.publish_bytes(f"repaired{extension}", rebuilt).path)
        if missing:
            outcome = "partial_content"
        elif diagnostics and not repaired:
            outcome = "partial_content"
        elif repaired:
            outcome = "repaired_package"
        else:
            outcome = "validated_original"
        return PackageRecovery(package_type, outcome, parts, missing, sorted(macro_parts), active, text, artifacts, rebuilt, diagnostics)

    def _recover_open_package(
        self,
        archive: zipfile.ZipFile,
        *,
        suffix: str,
        output_root: Path | None,
        limits: ResourceLimits,
        budget: BudgetTracker | None,
        goal: str | None,
    ) -> PackageRecovery:
        """Inspect a valid package ZIP without retaining all members in memory."""
        infos = sorted(archive.infolist(), key=lambda item: (item.filename.casefold(), item.header_offset))
        diagnostics: list[dict[str, Any]] = []
        if len(infos) > limits.max_archive_members:
            diagnostics.append({"budget": "archive_members", "declared": len(infos), "limit": limits.max_archive_members})
            infos = infos[:limits.max_archive_members]

        safe_infos: list[tuple[str, zipfile.ZipInfo]] = []
        seen: set[str] = set()
        for info in infos:
            try:
                safe = safe_relative_path(info.filename).as_posix()
            except PathLayoutError:
                diagnostics.append({"unsafe_path": info.filename})
                continue
            if safe in seen:
                diagnostics.append({"duplicate_rejected": info.filename})
                continue
            seen.add(safe)
            safe_infos.append((safe, info))

        names = {name for name, info in safe_infos if not info.is_dir()}
        mimetype = ""
        mimetype_info = next((info for name, info in safe_infos if name == "mimetype"), None)
        if mimetype_info is not None and not (mimetype_info.flag_bits & 1) and mimetype_info.file_size <= 4096:
            try:
                with archive.open(mimetype_info, "r") as reader:
                    mimetype = reader.read(4096).decode("ascii", errors="ignore")
            except (RuntimeError, zipfile.BadZipFile, NotImplementedError, OSError):
                pass
        package_type = _detect_type_from_names(names, suffix, mimetype)
        required = list(_REQUIRED.get(package_type, ()))
        missing = [name for name in required if name not in names]
        parts: list[DocumentPartResult] = []
        macro_parts: list[str] = []
        active = False
        text_fragments: list[str] = []
        text_chars = 0
        max_text_chars = min(16 * (1 << 20), limits.max_archive_member_bytes)
        artifacts: list[Path] = []
        writer = AtomicArtifactWriter(output_root, budget=budget) if output_root is not None else None
        publish_parts = goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}
        publish_text = goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.PREVIEW.value, RecoveryGoal.CARVE.value}
        total = 0

        for name, info in safe_infos:
            if info.is_dir():
                continue
            macro = name.lower().endswith("vbaproject.bin") or "macros/" in name.lower()
            embedded = "/embeddings/" in name.lower()
            part = DocumentPartResult(name, _media_type(name), name in required, macro=macro, active_content=macro or embedded)
            parts.append(part)
            if macro:
                macro_parts.append(name)
            active = active or part.active_content
            if info.flag_bits & 1:
                diagnostics.append({"encrypted": name})
                part.warning = "encrypted"
                continue
            if (
                info.file_size > limits.max_archive_member_bytes
                or total + info.file_size > limits.max_decompressed_bytes
                or (info.compress_size == 0 and info.file_size > 0)
                or (info.compress_size > 0 and info.file_size / info.compress_size > limits.max_expansion_ratio)
            ):
                diagnostics.append({"budget": "member_size_or_expansion", "member": name})
                part.warning = "budget_exceeded"
                continue

            is_xml = name.lower().endswith((".xml", ".rels"))
            should_publish_part = publish_parts and (
                "/media/" in name.lower()
                or embedded
                or name.startswith("Pictures/")
            )
            try:
                if is_xml:
                    with archive.open(info, "r") as reader:
                        extracted, parsed, warning, truncated, external = _xml_text_stream(
                            reader,
                            max_text_chars=max(0, max_text_chars - text_chars),
                        )
                    part.parsed = parsed
                    part.warning = warning
                    part.active_content = part.active_content or external
                    active = active or external
                    if truncated:
                        diagnostics.append({"text_truncated": name, "limit_chars": max_text_chars})
                    if extracted and name != "[Content_Types].xml" and not name.endswith(".rels"):
                        text_fragments.append(extracted)
                        text_chars += len(extracted)
                    if warning:
                        diagnostics.append({"xml_warning": name, "error": warning})
                elif should_publish_part and writer is not None:
                    with archive.open(info, "r") as reader:
                        published = writer.publish_stream(Path("parts") / safe_relative_path(name), _iter_reader(reader))
                    artifacts.append(published.path)
                else:
                    # Consume to EOF so ZipExtFile performs its CRC check without
                    # retaining the uncompressed member in memory.
                    with archive.open(info, "r") as reader:
                        for _ in _iter_reader(reader):
                            pass
            except BudgetExceeded:
                raise
            except (RuntimeError, zipfile.BadZipFile, NotImplementedError, OSError) as exc:
                diagnostics.append({"unreadable": name, "error": str(exc)})
                part.warning = str(exc)
                continue
            total += info.file_size

        text = "\n".join(dict.fromkeys(fragment for fragment in text_fragments if fragment))
        if writer is not None and text and publish_text:
            text_name = "preview.txt" if goal == RecoveryGoal.PREVIEW.value else "extracted-text.txt"
            artifacts.append(writer.publish_bytes(text_name, (text + "\n").encode("utf-8")).path)
        if missing:
            diagnostics.append({"missing_required": missing})
        outcome = "partial_content" if missing or diagnostics else "validated_original"
        return PackageRecovery(
            package_type,
            outcome,
            parts,
            missing,
            sorted(macro_parts),
            active,
            text,
            artifacts,
            None,
            diagnostics,
        )

    def recover_source(
        self,
        source: FileByteSource,
        *,
        suffix: str,
        output_root: Path | None = None,
        limits: ResourceLimits | None = None,
        budget: BudgetTracker | None = None,
        goal: str | None = None,
    ) -> PackageRecovery:
        limits = limits or ResourceLimits()
        source.assert_unchanged()
        try:
            with source.open_reader() as reader, zipfile.ZipFile(reader) as archive:
                result = self._recover_open_package(
                    archive,
                    suffix=suffix,
                    output_root=output_root,
                    limits=limits,
                    budget=budget,
                    goal=goal,
                )
            source.assert_unchanged()
            return result
        except (zipfile.BadZipFile, EOFError, OSError) as exc:
            if source.size > limits.max_materialized_bytes:
                return PackageRecovery(
                    _TYPE_FROM_SUFFIX.get(suffix.lower(), "unknown"),
                    "failed",
                    diagnostics=[
                        {"container_error": str(exc)},
                        {
                            "materialization_fallback": "not_run",
                            "source_bytes": source.size,
                            "limit": limits.max_materialized_bytes,
                        },
                    ],
                )
            data = source.slice(0, source.size).materialize()
            return self.recover_bytes(
                data,
                suffix=suffix,
                output_root=output_root,
                limits=limits,
                budget=budget,
                goal=goal,
            )

    def inspect(self, context: HandlerContext) -> InspectionResult:
        result = self.recover_source(context.source, suffix=context.record.path.suffix, limits=context.limits)
        return InspectionResult("package_document", result.outcome not in {"failed"}, 0.98 if result.outcome == "validated_original" else 0.72, diagnostics=result.diagnostics, parts=[{"name": part.name, "required": part.required, "parsed": part.parsed, "macro": part.macro, "active_content": part.active_content, "warning": part.warning} for part in result.parts], risk_flags=["active_content"] if result.active_content else [])

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        if goal not in {RecoveryGoal.REPAIR, RecoveryGoal.EXTRACT, RecoveryGoal.PREVIEW, RecoveryGoal.CARVE}:
            return []
        return [CandidatePlan(f"{self.handler_id}:{goal.value}", self.handler_id, goal.value, "package_document", goal.value, 100, (), estimated_materialized_bytes=0, estimated_output_bytes=context.source.size, meta={"source_mode": "stream", "fallback_materialization_limit": context.limits.max_materialized_bytes})]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        result = self.recover_source(
            context.source,
            suffix=context.record.path.suffix,
            output_root=context.output_root,
            limits=context.limits,
            budget=context.budget,
            goal=plan.goal,
        )
        ok = result.outcome != "failed"
        grade = OutcomeGrade.VALIDATED_ORIGINAL.value if result.outcome == "validated_original" else OutcomeGrade.PARTIAL_CONTENT.value if ok else OutcomeGrade.FAILED.value
        return RecoveryOutcome(None, DecodeResult(ok=ok, decoder=self.handler_id, telemetry={"package_type": result.package_type, "outcome": result.outcome, "missing_required": result.missing_required, "macro_parts": result.macro_parts, "active_content": result.active_content}), grade=grade, diagnostics=result.diagnostics)
