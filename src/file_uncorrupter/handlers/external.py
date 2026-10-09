from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..atomic import AtomicArtifactWriter
from ..budgets import BudgetTracker, ResourceLimits
from ..cancellation import CancellationToken
from ..paths import PathLayoutError, safe_relative_path
from ..process_runner import ProcessPolicy, probe_tool, run_process
from ..types import Artifact, CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome, SourceSliceSpec
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal
from .pdf import PDFHandler


@dataclass(slots=True)
class ExternalArchiveResult:
    family: str
    outcome: str
    members: list[dict[str, Any]] = field(default_factory=list)
    solid: bool = False
    volumes: int = 1
    tool_evidence: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class LegacyDocumentResult:
    family: str
    outcome: str
    text: str = ""
    macro: bool = False
    active_content: bool = False
    tool_evidence: dict[str, Any] = field(default_factory=dict)
    converted_path: Path | None = None


def parse_7z_listing(text: str) -> dict[str, Any]:
    blocks = [block.strip() for block in re.split(r"\r?\n\s*\r?\n", text) if block.strip()]
    parsed_blocks: list[dict[str, str]] = []
    for block in blocks:
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if line.strip().startswith("----------") or " = " not in line:
                continue
            key, value = line.split(" = ", 1)
            fields[key.strip()] = value.strip()
        if fields:
            parsed_blocks.append(fields)
    header = parsed_blocks[0] if parsed_blocks else {}
    members = []
    for fields in parsed_blocks[1:]:
        if "Path" not in fields:
            continue
        members.append(
            {
                "path": fields["Path"],
                "size": int(fields.get("Size", "0") or 0),
                "packed_size": int(fields.get("Packed Size", "0") or 0),
                "attributes": fields.get("Attributes", ""),
                "encrypted": fields.get("Encrypted") == "+",
                "method": fields.get("Method", ""),
                "crc": fields.get("CRC"),
            }
        )
    return {
        "type": header.get("Type", "unknown"),
        "solid": header.get("Solid") == "+",
        "volumes": int(header.get("Volumes", "1") or 1),
        "members": members,
    }


def _rtf_text(data: bytes) -> str:
    text = data.decode("latin-1", errors="replace")
    text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda match: bytes([int(match.group(1), 16)]).decode("cp1252", errors="replace"), text)
    text = re.sub(r"\\par\b", "\n", text)
    text = re.sub(r"\\tab\b", "\t", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = text.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")
    text = text.replace("{", "").replace("}", "")
    return " ".join(text.split())


def _probe_libreoffice(
    converter: str = "libreoffice",
    *,
    cancellation: CancellationToken | None = None,
):
    """Resolve LibreOffice's Unix and Windows command names consistently."""

    candidates = ("libreoffice", "soffice") if converter == "libreoffice" else (converter,)
    first_record = None
    for executable in candidates:
        record = probe_tool(
            executable,
            version_args=("--version",),
            policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=64 * 1024),
            cancellation=cancellation,
        )
        if first_record is None:
            first_record = record
        if record.available:
            return record
    assert first_record is not None
    return first_record


class ExternalAdapterHandler(FormatHandler):
    handler_id = "external-adapters-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        seven_zip = probe_tool("7z", version_args=("i",), policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=64 * 1024))
        libreoffice = _probe_libreoffice()
        return (
            CapabilityRecord(
                family="external_archive",
                variants=("7z", "rar"),
                extensions=(".7z", ".rar"),
                signatures=("7z-magic", "RAR-magic"),
                operations={"detect": "validated", "inspect": "partial", "validate": "baseline", "repair": "none", "normalize": "none", "extract": "baseline" if seven_zip.available else "none", "preview": "none", "carve": "none"},
                tools={"required": (), "optional": ("7z",)},
                limits={"max_decoder_seconds": 30, "max_tool_output_bytes": 1 << 20, "max_decompressed_bytes": 1 << 30},
                encryption="Encrypted archive entries are listed when possible; passwords are not guessed. Solid and multivolume boundaries are explicit.",
                active_content="Archive members are inert; links, devices, and unsafe paths are rejected.",
                outputs=({"kind": "extracted", "media_type": "application/octet-stream"},),
                fidelity="Extraction is available only when the exact 7z-compatible tool is recorded and bounded validation succeeds.",
                fixtures=("7z-tool-absent", "7z-listing"),
                availability="partial",
                handler_id=self.handler_id,
            ),
            CapabilityRecord(
                family="rtf",
                variants=("rtf",),
                extensions=(".rtf",),
                signatures=("RTF",),
                operations={"detect": "validated", "inspect": "partial", "validate": "baseline", "repair": "none", "normalize": "none", "extract": "partial", "preview": "partial", "carve": "none"},
                tools={"required": (), "optional": ()},
                limits={"max_decoder_seconds": 30, "max_tool_output_bytes": 1 << 20},
                encryption="not_applicable",
                active_content="RTF objects and embedded active content are reported and never executed.",
                outputs=({"kind": "extracted", "media_type": "text/plain"}, {"kind": "preview", "media_type": "text/plain"}),
                fidelity="RTF text is a partial inert extraction; formatting and embedded objects are not claimed as recovered.",
                fixtures=("rtf-active-object",),
                availability="partial",
                handler_id=self.handler_id,
            ),
            CapabilityRecord(
                family="legacy_office",
                variants=("doc", "xls", "ppt"),
                extensions=(".doc", ".xls", ".ppt"),
                signatures=("OLE-CFB",),
                operations={"detect": "validated", "inspect": "partial", "validate": "baseline", "repair": "none", "normalize": "none", "extract": "none", "preview": "partial" if libreoffice.available else "none", "carve": "none"},
                tools={"required": (), "optional": ("libreoffice",)},
                limits={"max_decoder_seconds": 30, "max_tool_output_bytes": 1 << 20},
                encryption="Encrypted legacy Office documents are reported; passwords are not guessed.",
                active_content="OLE macros and embedded active content are reported and never executed.",
                outputs=({"kind": "preview", "media_type": "application/pdf"},) if libreoffice.available else (),
                fidelity=(
                    "Detection and inert inspection are native. When LibreOffice is available, preview emits a PDF "
                    "validated by the native PDF handler; it is not editable Office recovery and may lose formatting, formulas, animations, or macros."
                    if libreoffice.available
                    else "Detection and inert inspection only. PDF preview is explicitly unavailable because LibreOffice is not available."
                ),
                fixtures=("ole-macro", "legacy-office-pdf-preview"),
                availability="partial",
                handler_id=self.handler_id,
            ),
        )

    def inspect_archive(
        self,
        path: Path,
        *,
        tool: str = "7z",
        limits: ResourceLimits | None = None,
        extract_root: Path | None = None,
        budget: BudgetTracker | None = None,
        cancellation: CancellationToken | None = None,
    ) -> ExternalArchiveResult:
        limits = limits or ResourceLimits()
        family = "rar" if path.suffix.lower() == ".rar" else "7z"
        record = probe_tool(
            tool,
            version_args=("i",),
            policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=64 * 1024),
            cancellation=cancellation,
        )
        evidence = {"available": record.available, "resolved_path": record.resolved_path, "version": record.version, "error": record.error}
        if not record.available or not record.resolved_path:
            return ExternalArchiveResult(family, "unavailable_dependency", tool_evidence=evidence)
        result = run_process(
            [record.resolved_path, "l", "-slt", "--", str(path.resolve())],
            ProcessPolicy(timeout_seconds=30, max_output_bytes=limits.max_tool_output_bytes),
            cancellation=cancellation,
        )
        evidence.update({"exit_code": result.returncode, "timed_out": result.timed_out, "output_truncated": result.output_truncated, "cleanup_ok": result.cleanup_ok})
        if result.timed_out:
            return ExternalArchiveResult(family, "budget_exceeded", tool_evidence=evidence)
        if result.returncode != 0 or result.output_truncated:
            return ExternalArchiveResult(family, "failed", tool_evidence=evidence)
        listing = parse_7z_listing(result.stdout.decode("utf-8", errors="replace"))
        members = listing["members"][: limits.max_archive_members]
        artifacts: list[Path] = []
        total = 0
        if extract_root is not None:
            writer = AtomicArtifactWriter(extract_root, budget=budget)
            for member in members:
                if member["encrypted"] or member["size"] > limits.max_archive_member_bytes:
                    member["outcome"] = "encrypted" if member["encrypted"] else "budget_exceeded"
                    continue
                try:
                    safe = safe_relative_path(member["path"])
                except PathLayoutError:
                    member["outcome"] = "unsafe_path"
                    continue
                if total + member["size"] > limits.max_decompressed_bytes:
                    member["outcome"] = "budget_exceeded"
                    continue
                extraction = run_process(
                    [record.resolved_path, "x", "-so", "--", str(path.resolve()), member["path"]],
                    ProcessPolicy(timeout_seconds=30, max_output_bytes=min(limits.max_archive_member_bytes, limits.max_tool_output_bytes)),
                    cancellation=cancellation,
                )
                if extraction.returncode != 0 or extraction.output_truncated:
                    member["outcome"] = "extraction_failed_or_bounded"
                    continue
                published = writer.publish_bytes(safe, extraction.stdout)
                artifacts.append(published.path)
                total += published.size
                member["outcome"] = "extracted"
        outcome = "partial_content" if any(member.get("encrypted") for member in members) else "validated_original"
        return ExternalArchiveResult(family, outcome, members, bool(listing["solid"]), int(listing["volumes"]), evidence, artifacts)

    def inspect_legacy_document(
        self,
        data: bytes,
        *,
        suffix: str,
        converter: str = "libreoffice",
        cancellation: CancellationToken | None = None,
    ) -> LegacyDocumentResult:
        if suffix.lower() == ".rtf" or data.startswith(b"{\\rtf"):
            active = b"\\object" in data.lower() or b"\\objdata" in data.lower()
            return LegacyDocumentResult("rtf", "partial_content", _rtf_text(data), False, active)
        ole = data.startswith(bytes.fromhex("d0cf11e0a1b11ae1"))
        macro = bool(re.search(rb"(?i)(?:VBA|Macros|PROJECTwm)", data))
        record = _probe_libreoffice(converter, cancellation=cancellation)
        if cancellation is not None:
            cancellation.checkpoint()
        evidence = {
            "available": record.available,
            "requested_name": converter,
            "executable_name": getattr(record, "name", converter),
            "resolved_path": record.resolved_path,
            "version": record.version,
            "error": record.error,
        }
        return LegacyDocumentResult("legacy-office" if ole else "unknown", "unavailable_dependency" if not record.available else "partial_content", "", macro, macro or ole, evidence)

    def convert_legacy_document(
        self,
        data: bytes,
        *,
        suffix: str,
        output_root: Path,
        converter: str = "libreoffice",
        limits: ResourceLimits | None = None,
        budget: BudgetTracker | None = None,
        cancellation: CancellationToken | None = None,
    ) -> LegacyDocumentResult:
        limits = limits or ResourceLimits()
        inspected = self.inspect_legacy_document(
            data,
            suffix=suffix,
            converter=converter,
            cancellation=cancellation,
        )
        if inspected.family != "legacy-office" or not inspected.tool_evidence.get("available"):
            return inspected
        resolved_path = inspected.tool_evidence.get("resolved_path")
        if not resolved_path:
            inspected.outcome = "unavailable_dependency"
            inspected.tool_evidence["error"] = "converter_path_missing"
            return inspected

        with tempfile.TemporaryDirectory(prefix="uncorrupter-libreoffice-") as directory:
            root = Path(directory).resolve()
            source = root / f"input{suffix.lower()}"
            converted_root = root / "converted"
            profile_root = root / "profile"
            converted_root.mkdir()
            profile_root.mkdir()
            source.write_bytes(data)
            command = [
                str(resolved_path),
                "--headless",
                "--safe-mode",
                "--nologo",
                "--nodefault",
                "--nolockcheck",
                "--norestore",
                f"-env:UserInstallation={profile_root.as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(converted_root),
                str(source),
            ]
            result = run_process(
                command,
                ProcessPolicy(
                    timeout_seconds=limits.max_decoder_seconds,
                    max_output_bytes=limits.max_tool_output_bytes,
                ),
                cancellation=cancellation,
            )
            inspected.tool_evidence.update(
                {
                    "name": "libreoffice",
                    "executable_name": inspected.tool_evidence.get("executable_name"),
                    "policy_id": "bounded-v1",
                    "operation": "pdf_preview",
                    "exit_code": result.returncode,
                    "timed_out": result.timed_out,
                    "cancelled": result.cancelled,
                    "duration_seconds": round(result.duration_seconds, 6),
                    "stdout_sha256": result.stdout_sha256,
                    "stderr_sha256": result.stderr_sha256,
                    "output_truncated": result.output_truncated,
                    "cleanup_ok": result.cleanup_ok,
                }
            )
            if result.cancelled and cancellation is not None:
                cancellation.checkpoint()
            if result.timed_out:
                inspected.outcome = "budget_exceeded"
                inspected.tool_evidence["error"] = "libreoffice_timeout"
                return inspected
            converted = converted_root / "input.pdf"
            if result.returncode != 0 or not converted.is_file() or converted.stat().st_size <= 0:
                inspected.outcome = "failed"
                inspected.tool_evidence["error"] = f"libreoffice_exit_{result.returncode}"
                return inspected
            if converted.stat().st_size > limits.max_materialized_bytes:
                inspected.outcome = "budget_exceeded"
                inspected.tool_evidence["error"] = "libreoffice_output_exceeds_materialization_limit"
                return inspected

            pdf_bytes = converted.read_bytes()
            analysis = PDFHandler().analyze_bytes(pdf_bytes)
            validated = (
                analysis.header_offset == 0
                and analysis.eof_present
                and analysis.xref_valid
                and analysis.object_count > 0
            )
            inspected.tool_evidence["validation"] = {
                "validator": "pdf-v1",
                "passed": validated,
                "objects": analysis.object_count,
                "pages": analysis.page_count,
                "xref_valid": analysis.xref_valid,
            }
            if not validated:
                inspected.outcome = "failed"
                inspected.tool_evidence["error"] = "converted_pdf_validation_failed"
                return inspected
            published = AtomicArtifactWriter(output_root, budget=budget).publish_bytes(
                "preview.pdf",
                pdf_bytes,
                validator=lambda path: (
                    (check := PDFHandler().analyze_bytes(path.read_bytes())).header_offset == 0
                    and check.eof_present
                    and check.xref_valid
                    and check.object_count > 0
                ),
            )
            inspected.converted_path = published.path
            inspected.outcome = "preview_only"
            inspected.tool_evidence["published_sha256"] = published.sha256
            inspected.tool_evidence["published_bytes"] = published.size
            return inspected

    def inspect(self, context: HandlerContext) -> InspectionResult:
        suffix = context.record.path.suffix.lower()
        if suffix in {".7z", ".rar"}:
            result = self.inspect_archive(
                context.record.path,
                limits=context.limits,
                cancellation=context.cancellation,
            )
            return InspectionResult("external_adapter", result.outcome not in {"failed"}, 0.8 if result.outcome == "validated_original" else 0.5, parts=result.members, risk_flags=["encrypted"] if any(member.get("encrypted") for member in result.members) else [])
        data = context.source.slice(0, min(context.source.size, context.limits.max_materialized_bytes)).materialize()
        legacy = self.inspect_legacy_document(data, suffix=suffix, cancellation=context.cancellation)
        return InspectionResult("external_adapter", legacy.family != "unknown", 0.8 if legacy.family != "unknown" else 0.2, diagnostics=[{"outcome": legacy.outcome, "tool": legacy.tool_evidence}], risk_flags=["active_content"] if legacy.active_content else [])

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        suffix = context.record.path.suffix.lower()
        supported = (
            goal == RecoveryGoal.EXTRACT
            if suffix in {".7z", ".rar"}
            else goal in {RecoveryGoal.EXTRACT, RecoveryGoal.PREVIEW}
            if suffix == ".rtf"
            else goal == RecoveryGoal.PREVIEW
            and suffix in {".doc", ".xls", ".ppt"}
            and _probe_libreoffice(cancellation=context.cancellation).available
        )
        context.cancellation.checkpoint()
        if not supported:
            return []
        return [CandidatePlan(f"{self.handler_id}:{goal.value}", self.handler_id, goal.value, "external_adapter", goal.value, 100, (SourceSliceSpec(0, context.source.size),), estimated_materialized_bytes=context.source.size)]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        suffix = context.record.path.suffix.lower()
        if suffix in {".7z", ".rar"}:
            result = self.inspect_archive(
                context.record.path,
                limits=context.limits,
                extract_root=context.output_root,
                budget=context.budget,
                cancellation=context.cancellation,
            )
            ok = result.outcome in {"validated_original", "partial_content"}
            grade = OutcomeGrade.PARTIAL_CONTENT.value if ok else OutcomeGrade.UNAVAILABLE_DEPENDENCY.value if result.outcome == "unavailable_dependency" else OutcomeGrade.FAILED.value
            return RecoveryOutcome(None, DecodeResult(ok=ok, decoder=self.handler_id, telemetry={"outcome": result.outcome, "members": result.members, "solid": result.solid, "volumes": result.volumes, "tool": result.tool_evidence}), grade=grade)
        data = plan.materialize(context.source, max_bytes=context.limits.max_materialized_bytes)
        if suffix in {".doc", ".xls", ".ppt"}:
            if context.output_root is None:
                return RecoveryOutcome(
                    None,
                    DecodeResult(ok=False, decoder=self.handler_id, error="legacy_preview_requires_output_root"),
                    grade=OutcomeGrade.FAILED.value,
                )
            legacy = self.convert_legacy_document(
                data,
                suffix=suffix,
                output_root=context.output_root,
                limits=context.limits,
                budget=context.budget,
                cancellation=context.cancellation,
            )
            ok = legacy.outcome == "preview_only" and legacy.converted_path is not None
            grade = (
                OutcomeGrade.PREVIEW_ONLY.value
                if ok
                else OutcomeGrade.UNAVAILABLE_DEPENDENCY.value
                if legacy.outcome == "unavailable_dependency"
                else OutcomeGrade.BUDGET_EXCEEDED.value
                if legacy.outcome == "budget_exceeded"
                else OutcomeGrade.FAILED.value
            )
            artifacts: list[Artifact] = []
            if ok and legacy.converted_path is not None:
                path = legacy.converted_path
                artifacts.append(
                    Artifact(
                        "preview",
                        path,
                        str(legacy.tool_evidence["published_sha256"]),
                        self.handler_id,
                        size=int(legacy.tool_evidence["published_bytes"]),
                        media_type="application/pdf",
                        fidelity_grade=grade,
                        validation_state="pdf_structure_validated",
                        validators=[legacy.tool_evidence["validation"]],
                        published=True,
                        meta={
                            "active_content_detected": legacy.active_content,
                            "macro_detected": legacy.macro,
                            "conversion": "inert_pdf_preview",
                        },
                    )
                )
            return RecoveryOutcome(
                None,
                DecodeResult(
                    ok=ok,
                    decoder=self.handler_id,
                    output_path=legacy.converted_path,
                    error="" if ok else str(legacy.tool_evidence.get("error") or legacy.outcome),
                    telemetry={
                        "family": legacy.family,
                        "outcome": legacy.outcome,
                        "macro": legacy.macro,
                        "active_content": legacy.active_content,
                        "tool": legacy.tool_evidence,
                    },
                ),
                artifacts=artifacts,
                grade=grade,
            )

        legacy = self.inspect_legacy_document(data, suffix=suffix, cancellation=context.cancellation)
        ok = bool(legacy.text)
        grade = OutcomeGrade.PREVIEW_ONLY.value if ok and plan.goal == RecoveryGoal.PREVIEW.value else OutcomeGrade.PARTIAL_CONTENT.value if ok else OutcomeGrade.UNAVAILABLE_DEPENDENCY.value if legacy.outcome == "unavailable_dependency" else OutcomeGrade.FAILED.value
        artifacts: list[Artifact] = []
        if ok and context.output_root is not None:
            name = "preview.txt" if plan.goal == RecoveryGoal.PREVIEW.value else "extracted-text.txt"
            kind = "preview" if plan.goal == RecoveryGoal.PREVIEW.value else "extracted"
            published = AtomicArtifactWriter(context.output_root, budget=context.budget).publish_bytes(name, (legacy.text + "\n").encode("utf-8"))
            artifacts.append(Artifact(kind, published.path, published.sha256, self.handler_id, size=published.size, media_type="text/plain; charset=utf-8", fidelity_grade=grade, validation_state="inert_text_extraction", published=True, meta={"active_content": legacy.active_content}))
        return RecoveryOutcome(None, DecodeResult(ok=ok, decoder=self.handler_id, telemetry={"family": legacy.family, "outcome": legacy.outcome, "macro": legacy.macro, "active_content": legacy.active_content, "tool": legacy.tool_evidence}), artifacts=artifacts, grade=grade)
