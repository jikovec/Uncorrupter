from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..atomic import AtomicArtifactWriter
from ..budgets import BudgetTracker, ResourceLimits
from ..byte_source import FileByteSource
from ..cancellation import CancellationToken
from ..process_runner import ProcessPolicy, probe_tool, run_process
from ..types import CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal


_OBJECT_RE = re.compile(rb"(?ms)(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj\b")
_OBJECT_HEADER_RE = re.compile(rb"(?m)(\d+)\s+(\d+)\s+obj\b")
_STARTXREF_RE = re.compile(rb"startxref\s+(\d+)")


@dataclass(slots=True)
class PDFAnalysis:
    header_offset: int
    eof_present: bool
    object_count: int
    object_offsets: dict[int, tuple[int, int]]
    xref_offset: int | None
    xref_valid: bool
    page_count: int
    stream_count: int
    encrypted: bool
    text: str
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class PDFRecovery:
    outcome: str
    object_count: int
    page_count: int
    stream_count: int
    xref_valid: bool
    encrypted: bool
    prefix_bytes: int
    text: str
    rebuilt_bytes: bytes | None = None
    artifacts: list[Path] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    tool_evidence: dict[str, Any] = field(default_factory=dict)


def _literal_text(payload: bytes) -> str:
    values: list[str] = []
    for match in re.finditer(rb"\((?:\\.|[^\\)])*\)\s*Tj", payload):
        raw = match.group(0)
        raw = raw[1:raw.rfind(b")")]
        raw = re.sub(rb"\\([\\()])", rb"\1", raw)
        raw = raw.replace(b"\\n", b"\n").replace(b"\\r", b"\r").replace(b"\\t", b"\t")
        values.append(raw.decode("latin-1", errors="replace"))
    for array in re.finditer(rb"\[(.*?)\]\s*TJ", payload, re.S):
        fragments = re.findall(rb"\((?:\\.|[^\\)])*\)", array.group(1))
        if fragments:
            values.append("".join(fragment[1:-1].decode("latin-1", errors="replace") for fragment in fragments))
    return "\n".join(dict.fromkeys(value for value in values if value))


def _file_chunks(path: Path, chunk_size: int = 1 << 20):
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


class PDFHandler(FormatHandler):
    handler_id = "pdf-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        qpdf = probe_tool("qpdf", version_args=("--version",), policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=16 * 1024))
        return (
            CapabilityRecord(
                family="pdf",
                variants=("pdf",),
                extensions=(".pdf",),
                signatures=("%PDF-", "obj/endobj", "xref/startxref", "trailer/%%EOF"),
                operations={"detect": "validated", "inspect": "validated", "validate": "validated", "repair": "partial", "normalize": "none", "extract": "partial", "preview": "none", "carve": "partial"},
                tools={"required": (), "optional": ("qpdf",)},
                limits={"max_materialized_bytes": 256 * (1 << 20), "max_tool_output_bytes": 1 << 20},
                encryption="Encryption dictionaries are reported; encrypted content is not decrypted or repaired.",
                active_content="Embedded files and actions are reported as inert structure and never executed.",
                outputs=({"kind": "repaired", "media_type": "application/pdf"}, {"kind": "extracted", "media_type": "text/plain"}, {"kind": "diagnostics", "media_type": "application/json"}),
                fidelity="Native repair strips an unambiguous prefix, appends EOF, and rebuilds a classic xref from explicit object headers; it does not invent page content.",
                fixtures=("pdf-valid", "pdf-prefix", "pdf-missing-xref", "pdf-encrypted"),
                availability="available",
                handler_id=self.handler_id,
            ),
        )

    def analyze_bytes(self, data: bytes) -> PDFAnalysis:
        header_offset = data.find(b"%PDF-")
        eof_present = data.rstrip().endswith(b"%%EOF")
        object_offsets: dict[int, tuple[int, int]] = {}
        diagnostics: list[dict[str, Any]] = []
        for match in _OBJECT_RE.finditer(data):
            number = int(match.group(1))
            generation = int(match.group(2))
            if number in object_offsets:
                diagnostics.append({"duplicate_object": number, "offset": match.start()})
                continue
            object_offsets[number] = (match.start(), generation)
            body = match.group(3)
            stream = re.search(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S)
            if stream:
                declared = re.search(rb"/Length\s+(\d+)", body[:stream.start()])
                if declared and int(declared.group(1)) != len(stream.group(1)):
                    diagnostics.append({"object": number, "stream_length_declared": int(declared.group(1)), "stream_length_observed": len(stream.group(1))})
        startxrefs = [int(value) for value in _STARTXREF_RE.findall(data)]
        xref_offset = startxrefs[-1] if startxrefs else None
        xref_valid = False
        if xref_offset is not None and 0 <= xref_offset < len(data):
            window = data[xref_offset:xref_offset + 256]
            xref_valid = window.startswith(b"xref") or b"/Type /XRef" in window
        pages = len(re.findall(rb"/Type\s*/Page(?!s)\b", data))
        streams = len(re.findall(rb"\bstream\r?\n", data))
        encrypted = bool(re.search(rb"/Encrypt\b", data))
        text = _literal_text(data)
        if header_offset < 0:
            diagnostics.append({"error": "pdf_header_missing"})
        elif header_offset > 0:
            diagnostics.append({"prefix_bytes": header_offset})
        if not eof_present:
            diagnostics.append({"error": "pdf_eof_missing"})
        if not xref_valid:
            diagnostics.append({"error": "xref_missing_or_invalid", "startxref": xref_offset})
        if re.search(rb"/EmbeddedFile\b", data):
            diagnostics.append({"risk": "embedded_file"})
        if re.search(rb"/(?:JavaScript|JS|OpenAction|Launch)\b", data):
            diagnostics.append({"risk": "active_action"})
        return PDFAnalysis(header_offset, eof_present, len(object_offsets), object_offsets, xref_offset, xref_valid, pages, streams, encrypted, text, diagnostics)

    def analyze_source(self, source: FileByteSource, *, text_limit_chars: int = 16 * (1 << 20)) -> PDFAnalysis:
        """Incrementally collect bounded PDF structure and text evidence."""
        header_offset = -1
        object_offsets: dict[int, tuple[int, int]] = {}
        duplicate_objects: list[dict[str, int]] = []
        page_offsets: set[int] = set()
        stream_offsets: set[int] = set()
        text_values: list[str] = []
        text_seen: set[str] = set()
        text_chars = 0
        encrypted = False
        embedded = False
        active = False
        carry = b""
        absolute = 0
        tail_limit = min(source.size, 2 * (1 << 20))
        tail = b""
        overlap = 4096

        for chunk in source.iter_chunks(chunk_size=1 << 20):
            window = carry + chunk
            base = absolute - len(carry)
            if header_offset < 0:
                found = window.find(b"%PDF-")
                if found >= 0:
                    header_offset = base + found
            for match in _OBJECT_HEADER_RE.finditer(window):
                offset = base + match.start()
                # Matches wholly inside the carry were already recorded.
                if offset + len(match.group(0)) <= absolute:
                    continue
                number = int(match.group(1))
                generation = int(match.group(2))
                if number in object_offsets and object_offsets[number][0] != offset:
                    duplicate_objects.append({"duplicate_object": number, "offset": offset})
                else:
                    object_offsets[number] = (offset, generation)
            for match in re.finditer(rb"/Type\s*/Page(?!s)\b", window):
                offset = base + match.start()
                if offset + len(match.group(0)) > absolute:
                    page_offsets.add(offset)
            for match in re.finditer(rb"\bstream\r?\n", window):
                offset = base + match.start()
                if offset + len(match.group(0)) > absolute:
                    stream_offsets.add(offset)
            encrypted = encrypted or bool(re.search(rb"/Encrypt\b", window))
            embedded = embedded or bool(re.search(rb"/EmbeddedFile\b", window))
            active = active or bool(re.search(rb"/(?:JavaScript|JS|OpenAction|Launch)\b", window))
            for value in _literal_text(window).splitlines():
                if not value or value in text_seen:
                    continue
                remaining = text_limit_chars - text_chars
                if remaining <= 0:
                    break
                selected = value[:remaining]
                text_seen.add(value)
                text_values.append(selected)
                text_chars += len(selected)
            tail = (tail + chunk)[-tail_limit:] if tail_limit else b""
            carry = window[-overlap:]
            absolute += len(chunk)

        eof_present = tail.rstrip().endswith(b"%%EOF")
        startxrefs = [int(value) for value in _STARTXREF_RE.findall(tail)]
        xref_offset = startxrefs[-1] if startxrefs else None
        xref_valid = False
        if xref_offset is not None and 0 <= xref_offset < source.size:
            tail_start = source.size - len(tail)
            if xref_offset >= tail_start:
                window = tail[xref_offset - tail_start:xref_offset - tail_start + 256]
                xref_valid = window.startswith(b"xref") or b"/Type /XRef" in window
            elif source.budget.remaining("scanned_bytes") >= min(256, source.size - xref_offset):
                window = source.read(xref_offset, min(256, source.size - xref_offset))
                xref_valid = window.startswith(b"xref") or b"/Type /XRef" in window

        diagnostics: list[dict[str, Any]] = [
            {
                "analysis": "streaming",
                "source_bytes": source.size,
                "text_limit_chars": text_limit_chars,
                "text_truncated": text_chars >= text_limit_chars,
            }
        ]
        diagnostics.extend(duplicate_objects)
        if header_offset < 0:
            diagnostics.append({"error": "pdf_header_missing"})
        elif header_offset > 0:
            diagnostics.append({"prefix_bytes": header_offset})
        if not eof_present:
            diagnostics.append({"error": "pdf_eof_missing"})
        if not xref_valid:
            diagnostics.append({"error": "xref_missing_or_invalid", "startxref": xref_offset})
        if embedded:
            diagnostics.append({"risk": "embedded_file"})
        if active:
            diagnostics.append({"risk": "active_action"})
        return PDFAnalysis(
            header_offset,
            eof_present,
            len(object_offsets),
            object_offsets,
            xref_offset,
            xref_valid,
            len(page_offsets),
            len(stream_offsets),
            encrypted,
            "\n".join(text_values),
            diagnostics,
        )

    def analyze_path(self, path: Path) -> PDFAnalysis:
        size = Path(path).stat().st_size
        limits = ResourceLimits(
            max_source_bytes=max(1, size),
            max_scanned_bytes=max(1, size + 512),
        )
        return self.analyze_source(FileByteSource(path, limits=limits))

    def _rebuild(self, data: bytes, analysis: PDFAnalysis) -> bytes | None:
        if analysis.header_offset < 0 or not analysis.object_offsets:
            return None
        base = bytearray(
            re.sub(rb"(?:\s*startxref\s+\d+\s*)?%%EOF\s*$", b"", data[analysis.header_offset:], flags=re.S).rstrip()
            + b"\n"
        )
        objects: dict[int, tuple[int, int]] = {}
        for match in _OBJECT_RE.finditer(base):
            objects.setdefault(int(match.group(1)), (match.start(), int(match.group(2))))
        if not objects:
            return None
        maximum = max(objects)
        root = re.search(rb"/Root\s+(\d+)\s+(\d+)\s+R", base)
        if root is None:
            catalog = next((number for number, _ in objects.items() if re.search(rb"/Type\s*/Catalog\b", next(match.group(3) for match in _OBJECT_RE.finditer(base) if int(match.group(1)) == number))), None)
            root_ref = f" /Root {catalog} 0 R" if catalog is not None else ""
        else:
            root_ref = f" /Root {int(root.group(1))} {int(root.group(2))} R"
        xref_offset = len(base)
        lines = [f"xref\n0 {maximum + 1}\n", "0000000000 65535 f \n"]
        for number in range(1, maximum + 1):
            if number in objects:
                offset, generation = objects[number]
                lines.append(f"{offset:010d} {generation:05d} n \n")
            else:
                lines.append("0000000000 00000 f \n")
        lines.append(f"trailer\n<< /Size {maximum + 1}{root_ref} >>\nstartxref\n{xref_offset}\n%%EOF\n")
        base.extend("".join(lines).encode("ascii"))
        return bytes(base)

    def recover_bytes(
        self,
        data: bytes,
        *,
        output_root: Path | None = None,
        use_qpdf: bool = False,
        qpdf_path: str = "qpdf",
        budget: BudgetTracker | None = None,
        cancellation: CancellationToken | None = None,
        goal: str | None = None,
        max_tool_artifact_bytes: int = 256 * (1 << 20),
    ) -> PDFRecovery:
        analysis = self.analyze_bytes(data)
        if analysis.encrypted:
            outcome = "encrypted"
            rebuilt = None
        elif analysis.header_offset == 0 and analysis.eof_present and analysis.xref_valid:
            outcome = "validated_original"
            rebuilt = None
        else:
            rebuilt = self._rebuild(data, analysis)
            outcome = "repaired" if rebuilt is not None and self.analyze_bytes(rebuilt).xref_valid else "partial_content" if analysis.object_count else "failed"
        tool: dict[str, Any] = {}
        if use_qpdf:
            record = probe_tool(
                qpdf_path,
                version_args=("--version",),
                policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=16 * 1024),
                cancellation=cancellation,
            )
            tool = {
                "name": "qpdf",
                "available": record.available,
                "resolved_path": record.resolved_path,
                "version": record.version,
                "error": record.error,
                "runs": [],
            }
            if cancellation is not None:
                cancellation.checkpoint()
            if record.available and record.resolved_path:
                with tempfile.TemporaryDirectory(prefix="uncorrupter-qpdf-") as directory:
                    root = Path(directory)
                    source = root / "input.pdf"
                    source.write_bytes(rebuilt or data)
                    if cancellation is not None:
                        cancellation.checkpoint()

                    # A structurally valid input only needs independent validation.
                    # Damaged input is rewritten by qpdf before that exact output is
                    # validated and considered for publication.
                    qpdf_candidate = source
                    if outcome != "validated_original":
                        qpdf_candidate = root / "repaired.pdf"
                        repair_result = run_process(
                            [record.resolved_path, str(source), str(qpdf_candidate)],
                            ProcessPolicy(timeout_seconds=20, max_output_bytes=1 << 20),
                            cancellation=cancellation,
                        )
                        tool["runs"].append(self._qpdf_run_evidence("repair", repair_result))
                        if repair_result.cancelled and cancellation is not None:
                            cancellation.checkpoint()
                        if (
                            repair_result.returncode not in {0, 3}
                            or repair_result.timed_out
                            or repair_result.cancelled
                            or not qpdf_candidate.is_file()
                            or qpdf_candidate.stat().st_size <= 0
                        ):
                            qpdf_candidate = source
                        elif qpdf_candidate.stat().st_size > max_tool_artifact_bytes:
                            tool["error"] = "qpdf_output_exceeds_materialization_limit"
                            qpdf_candidate = source

                    check_result = run_process(
                        [record.resolved_path, "--check", str(qpdf_candidate)],
                        ProcessPolicy(timeout_seconds=20, max_output_bytes=1 << 20),
                        cancellation=cancellation,
                    )
                    tool["runs"].append(self._qpdf_run_evidence("check", check_result))
                    if check_result.cancelled and cancellation is not None:
                        cancellation.checkpoint()
                    tool["validated"] = (
                        check_result.returncode in {0, 3}
                        and not check_result.timed_out
                        and not check_result.cancelled
                    )

                    if qpdf_candidate != source and tool["validated"]:
                        candidate_bytes = qpdf_candidate.read_bytes()
                        candidate_analysis = self.analyze_bytes(candidate_bytes)
                        tool["native_validation"] = {
                            "header": candidate_analysis.header_offset == 0,
                            "eof": candidate_analysis.eof_present,
                            "xref": candidate_analysis.xref_valid,
                            "objects": candidate_analysis.object_count,
                        }
                        if (
                            candidate_analysis.header_offset == 0
                            and candidate_analysis.eof_present
                            and candidate_analysis.xref_valid
                            and candidate_analysis.object_count > 0
                        ):
                            rebuilt = candidate_bytes
                            outcome = "repaired"

        artifacts: list[Path] = []
        if output_root is not None:
            writer = AtomicArtifactWriter(output_root, budget=budget)
            if rebuilt is not None and (goal is None or goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value}):
                artifacts.append(writer.publish_bytes("repaired.pdf", rebuilt, validator=lambda path: self.analyze_bytes(path.read_bytes()).xref_valid).path)
            if analysis.text and (goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}):
                artifacts.append(writer.publish_bytes("extracted-text.txt", (analysis.text + "\n").encode("utf-8")).path)
        result_analysis = self.analyze_bytes(rebuilt) if rebuilt is not None else analysis
        return PDFRecovery(
            outcome,
            result_analysis.object_count,
            result_analysis.page_count,
            result_analysis.stream_count,
            result_analysis.xref_valid,
            analysis.encrypted,
            max(0, analysis.header_offset),
            result_analysis.text or analysis.text,
            rebuilt,
            artifacts,
            analysis.diagnostics,
            tool,
        )

    @staticmethod
    def _qpdf_run_evidence(operation: str, result: Any) -> dict[str, Any]:
        return {
            "operation": operation,
            "exit_code": result.returncode,
            "timed_out": result.timed_out,
            "cancelled": result.cancelled,
            "duration_seconds": result.duration_seconds,
            "stdout_sha256": result.stdout_sha256,
            "stderr_sha256": result.stderr_sha256,
            "output_truncated": result.output_truncated,
            "cleanup_ok": result.cleanup_ok,
        }

    def recover_source(
        self,
        source: FileByteSource,
        *,
        output_root: Path | None = None,
        use_qpdf: bool = False,
        qpdf_path: str = "qpdf",
        budget: BudgetTracker | None = None,
        cancellation: CancellationToken | None = None,
        goal: str | None = None,
        max_tool_artifact_bytes: int = 2 * (1 << 30),
    ) -> PDFRecovery:
        cancellation = cancellation or CancellationToken()
        cancellation.checkpoint()
        analysis = self.analyze_source(source)
        if analysis.encrypted:
            outcome = "encrypted"
        elif analysis.header_offset == 0 and analysis.eof_present and analysis.xref_valid:
            outcome = "validated_original"
        elif analysis.object_count:
            outcome = "partial_content"
        else:
            outcome = "failed"
        result_analysis = analysis
        artifacts: list[Path] = []
        tool: dict[str, Any] = {}

        if use_qpdf and not analysis.encrypted:
            record = probe_tool(
                qpdf_path,
                version_args=("--version",),
                policy=ProcessPolicy(timeout_seconds=5, max_output_bytes=16 * 1024),
                cancellation=cancellation,
            )
            tool = {
                "name": "qpdf",
                "available": record.available,
                "resolved_path": record.resolved_path,
                "version": record.version,
                "error": record.error,
                "source_mode": "direct_path",
                "runs": [],
            }
            cancellation.checkpoint()
            if record.available and record.resolved_path:
                with tempfile.TemporaryDirectory(prefix="uncorrupter-qpdf-") as directory:
                    root = Path(directory)
                    candidate_path = source.path
                    if outcome != "validated_original":
                        candidate_path = root / "repaired.pdf"
                        repair_result = run_process(
                            [record.resolved_path, str(source.path), str(candidate_path)],
                            ProcessPolicy(timeout_seconds=20, max_output_bytes=1 << 20),
                            cancellation=cancellation,
                        )
                        tool["runs"].append(self._qpdf_run_evidence("repair", repair_result))
                        if repair_result.cancelled:
                            cancellation.checkpoint()
                        if (
                            repair_result.returncode not in {0, 3}
                            or repair_result.timed_out
                            or not candidate_path.is_file()
                            or candidate_path.stat().st_size <= 0
                        ):
                            candidate_path = source.path
                        elif candidate_path.stat().st_size > max_tool_artifact_bytes:
                            tool["error"] = "qpdf_output_exceeds_artifact_limit"
                            candidate_path = source.path

                    check_result = run_process(
                        [record.resolved_path, "--check", str(candidate_path)],
                        ProcessPolicy(timeout_seconds=20, max_output_bytes=1 << 20),
                        cancellation=cancellation,
                    )
                    tool["runs"].append(self._qpdf_run_evidence("check", check_result))
                    if check_result.cancelled:
                        cancellation.checkpoint()
                    tool["validated"] = (
                        check_result.returncode in {0, 3}
                        and not check_result.timed_out
                        and not check_result.cancelled
                    )
                    if candidate_path != source.path and tool["validated"]:
                        candidate_analysis = self.analyze_path(candidate_path)
                        tool["native_validation"] = {
                            "header": candidate_analysis.header_offset == 0,
                            "eof": candidate_analysis.eof_present,
                            "xref": candidate_analysis.xref_valid,
                            "objects": candidate_analysis.object_count,
                            "source_mode": "streaming",
                        }
                        if (
                            candidate_analysis.header_offset == 0
                            and candidate_analysis.eof_present
                            and candidate_analysis.xref_valid
                            and candidate_analysis.object_count > 0
                        ):
                            if output_root is not None and goal in {None, RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value}:
                                published = AtomicArtifactWriter(output_root, budget=budget).publish_stream(
                                    "repaired.pdf",
                                    _file_chunks(candidate_path),
                                    validator=lambda path: self.analyze_path(path).xref_valid,
                                )
                                artifacts.append(published.path)
                                tool["output"] = {
                                    "path": str(published.path),
                                    "sha256": published.sha256,
                                    "size": published.size,
                                    "atomic": published.atomic,
                                }
                            outcome = "repaired"
                            result_analysis = candidate_analysis

        should_materialize = (
            source.size <= source.limits.max_materialized_bytes
            and outcome != "repaired"
            and (
                outcome != "validated_original"
                or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}
            )
        )
        if should_materialize:
            data = source.slice(0, source.size).materialize()
            native = self.recover_bytes(
                data,
                output_root=output_root,
                use_qpdf=False,
                budget=budget,
                cancellation=cancellation,
                goal=goal,
                max_tool_artifact_bytes=max_tool_artifact_bytes,
            )
            native.tool_evidence = tool
            native.diagnostics.insert(
                0,
                {
                    "source_mode": "bounded_materialization_fallback",
                    "source_bytes": source.size,
                    "limit": source.limits.max_materialized_bytes,
                },
            )
            return native

        if (
            source.size > source.limits.max_materialized_bytes
            and outcome not in {"validated_original", "repaired"}
        ):
            analysis.diagnostics.append(
                {
                    "materialization_fallback": "not_run",
                    "source_bytes": source.size,
                    "limit": source.limits.max_materialized_bytes,
                }
            )
        if (
            output_root is not None
            and result_analysis.text
            and goal in {None, RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}
        ):
            artifacts.append(
                AtomicArtifactWriter(output_root, budget=budget)
                .publish_bytes("extracted-text.txt", (result_analysis.text + "\n").encode("utf-8"))
                .path
            )
        source.assert_unchanged()
        return PDFRecovery(
            outcome,
            result_analysis.object_count,
            result_analysis.page_count,
            result_analysis.stream_count,
            result_analysis.xref_valid,
            analysis.encrypted,
            max(0, analysis.header_offset),
            result_analysis.text or analysis.text,
            None,
            artifacts,
            analysis.diagnostics,
            tool,
        )

    def inspect(self, context: HandlerContext) -> InspectionResult:
        analysis = self.analyze_source(context.source)
        return InspectionResult("pdf", analysis.header_offset >= 0 and bool(analysis.object_count), 0.98 if analysis.xref_valid else 0.72, diagnostics=analysis.diagnostics, parts=[{"objects": analysis.object_count, "pages": analysis.page_count, "streams": analysis.stream_count}], risk_flags=[item["risk"] for item in analysis.diagnostics if "risk" in item])

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        if goal not in {RecoveryGoal.REPAIR, RecoveryGoal.EXTRACT, RecoveryGoal.CARVE}:
            return []
        return [CandidatePlan(f"{self.handler_id}:{goal.value}", self.handler_id, goal.value, "pdf", goal.value, 100, (), estimated_materialized_bytes=0, estimated_output_bytes=context.source.size, meta={"source_mode": "stream", "fallback_materialization_limit": context.limits.max_materialized_bytes})]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        result = self.recover_source(
            context.source,
            output_root=context.output_root,
            use_qpdf=plan.goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value},
            budget=context.budget,
            cancellation=context.cancellation,
            goal=plan.goal,
            max_tool_artifact_bytes=context.limits.max_output_bytes,
        )
        ok = result.outcome in {"validated_original", "repaired", "partial_content"}
        grade = OutcomeGrade.VALIDATED_ORIGINAL.value if result.outcome == "validated_original" else OutcomeGrade.PARTIAL_CONTENT.value if ok else OutcomeGrade.FAILED.value
        return RecoveryOutcome(None, DecodeResult(ok=ok, decoder=self.handler_id, telemetry={"outcome": result.outcome, "objects": result.object_count, "pages": result.page_count, "streams": result.stream_count, "xref_valid": result.xref_valid, "encrypted": result.encrypted, "tool": result.tool_evidence}), grade=grade, diagnostics=result.diagnostics)
