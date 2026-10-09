from __future__ import annotations

import binascii
import io
import stat
import struct
import tarfile
import zipfile
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..atomic import AtomicArtifactWriter
from ..budgets import BudgetExceeded, BudgetTracker, ResourceLimits
from ..byte_source import FileByteSource
from ..paths import PathLayoutError, safe_relative_path
from ..types import CandidatePlan, DecodeResult, OutcomeGrade, RecoveryOutcome
from .base import CapabilityRecord, FormatHandler, HandlerContext, InspectionResult, RecoveryGoal


@dataclass(slots=True)
class ArchiveMemberResult:
    original_name: str
    safe_name: str | None
    header_offset: int
    method: str
    compressed_size: int
    uncompressed_size: int
    checksum: str | None
    encrypted: bool = False
    outcome: str = "inspected"
    diagnostic: str = ""
    artifact_path: Path | None = None


@dataclass(slots=True)
class ArchiveRecovery:
    format: str
    outcome: str
    members: list[ArchiveMemberResult] = field(default_factory=list)
    rebuilt_bytes: bytes | None = None
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


def _safe_name(name: str) -> str | None:
    try:
        return safe_relative_path(name).as_posix()
    except PathLayoutError:
        return None


def _chunks(data: bytes, size: int = 1 << 20) -> Iterable[bytes]:
    for offset in range(0, len(data), size):
        yield data[offset:offset + size]


def _publish(output_root: Path | None, name: str, payload: bytes, budget: BudgetTracker | None = None) -> Path | None:
    if output_root is None:
        return None
    return AtomicArtifactWriter(output_root, budget=budget).publish_stream(name, _chunks(payload)).path


def _reader_chunks(reader: Any, size: int = 1 << 20) -> Iterable[bytes]:
    while True:
        chunk = reader.read(size)
        if not chunk:
            return
        yield chunk


def _publish_reader(
    output_root: Path | None,
    name: str,
    reader: Any,
    budget: BudgetTracker | None = None,
) -> Path | None:
    if output_root is None:
        for _ in _reader_chunks(reader):
            pass
        return None
    return AtomicArtifactWriter(output_root, budget=budget).publish_stream(name, _reader_chunks(reader)).path


def _ratio_exceeded(compressed: int, uncompressed: int, limits: ResourceLimits) -> bool:
    if uncompressed > limits.max_archive_member_bytes:
        return True
    if compressed == 0:
        return uncompressed > 0
    return uncompressed / compressed > limits.max_expansion_ratio


class ArchiveHandler(FormatHandler):
    handler_id = "archive-v1"

    def capabilities(self) -> tuple[CapabilityRecord, ...]:
        return (
            CapabilityRecord(
                family="archive",
                variants=("zip", "tar"),
                extensions=(".zip", ".tar"),
                signatures=("PK:local", "PK:central", "ustar-checksum"),
                operations={"detect": "validated", "inspect": "validated", "validate": "validated", "repair": "partial", "normalize": "none", "extract": "validated", "preview": "none", "carve": "partial"},
                tools={"required": (), "optional": ()},
                limits={"max_archive_members": 10_000, "max_decompressed_bytes": 1 << 30, "max_expansion_ratio": 100.0, "max_nesting_depth": 3},
                encryption="Encrypted members are identified and never cracked or extracted without explicit future credential support.",
                active_content="Members are treated as inert bytes; links and devices are rejected.",
                outputs=({"kind": "repaired", "media_type": "application/zip"}, {"kind": "extracted", "media_type": "application/octet-stream"}, {"kind": "diagnostics", "media_type": "application/json"}),
                fidelity="Valid members require bounded decompression and checksum validation; ambiguous local-header entries are not reconstructed.",
                fixtures=("zip-valid", "zip-local-only", "zip-traversal", "zip-bomb", "tar-resync"),
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
        depth: int = 0,
        budget: BudgetTracker | None = None,
        goal: str | None = None,
    ) -> ArchiveRecovery:
        limits = limits or ResourceLimits()
        extract_members = goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}
        publish_repair = goal is None or goal in {RecoveryGoal.REPAIR.value, RecoveryGoal.CARVE.value}
        if depth > limits.max_nesting_depth:
            return ArchiveRecovery("unknown", "budget_exceeded", diagnostics=[{"budget": "nesting_depth"}])
        if suffix.lower() == ".tar" or (len(data) >= 512 and data[257:262] == b"ustar"):
            return self._recover_tar(data, output_root, limits, budget, extract_members, publish_repair)
        return self._recover_zip(data, output_root, limits, budget, extract_members, publish_repair)

    def _recover_zip(self, data: bytes, output_root: Path | None, limits: ResourceLimits, budget: BudgetTracker | None, extract_members: bool, publish_repair: bool) -> ArchiveRecovery:
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
            infos = archive.infolist()
            central_valid = True
        except (zipfile.BadZipFile, EOFError):
            archive = None
            infos = []
            central_valid = False
        if central_valid and archive is not None:
            try:
                return self._recover_open_zip(archive, infos, output_root, limits, budget, extract_members)
            finally:
                archive.close()

        local = self._scan_zip_locals(data, limits)
        recovered = [(member, payload) for member, payload in local if member.outcome == "validated"]
        rebuilt = None
        if recovered:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for member, payload in sorted(recovered, key=lambda item: item[0].safe_name or ""):
                    assert member.safe_name is not None
                    info = zipfile.ZipInfo(member.safe_name, (1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    target.writestr(info, payload)
                    if extract_members:
                        try:
                            member.artifact_path = _publish(output_root, member.safe_name, payload, budget)
                            member.outcome = "extracted"
                        except BudgetExceeded:
                            raise
                        except Exception as exc:
                            member.outcome = "publication_failed"
                            member.diagnostic = str(exc)
                    else:
                        member.outcome = "validated"
            rebuilt = buffer.getvalue()
            if output_root is not None and publish_repair:
                _publish(output_root, "repaired.zip", rebuilt, budget)
        outcome = "reconstructed" if rebuilt is not None else ("budget_exceeded" if any(member.outcome == "budget_exceeded" for member, _ in local) else "failed")
        return ArchiveRecovery("zip", outcome, [member for member, _ in local], rebuilt, [{"central_directory": "missing_or_invalid"}])

    def _recover_open_zip(
        self,
        archive: zipfile.ZipFile,
        infos: list[zipfile.ZipInfo],
        output_root: Path | None,
        limits: ResourceLimits,
        budget: BudgetTracker | None,
        extract_members: bool,
    ) -> ArchiveRecovery:
        """Validate/extract a central-directory ZIP without whole-file reads."""
        members: list[ArchiveMemberResult] = []
        names: set[str] = set()
        total = 0
        budget_failed = False
        for index, info in enumerate(sorted(infos, key=lambda item: (item.filename.casefold(), item.header_offset))):
            member = ArchiveMemberResult(
                info.filename,
                _safe_name(info.filename),
                int(info.header_offset),
                str(info.compress_type),
                int(info.compress_size),
                int(info.file_size),
                f"{info.CRC:08x}",
                encrypted=bool(info.flag_bits & 1),
            )
            members.append(member)
            if index >= limits.max_archive_members:
                member.outcome = "budget_exceeded"
                member.diagnostic = "archive_member_count"
                budget_failed = True
                continue
            if member.safe_name is None:
                member.outcome = "unsafe_path"
                continue
            if member.safe_name in names:
                member.outcome = "duplicate_rejected"
                continue
            names.add(member.safe_name)
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode) or stat.S_ISCHR(unix_mode) or stat.S_ISBLK(unix_mode):
                member.outcome = "link_or_device_rejected"
                continue
            if info.is_dir():
                member.outcome = "directory"
                continue
            if member.encrypted:
                member.outcome = "encrypted"
                continue
            if _ratio_exceeded(info.compress_size, info.file_size, limits):
                member.outcome = "budget_exceeded"
                member.diagnostic = "member_size_or_expansion_ratio"
                budget_failed = True
                continue
            if total + info.file_size > limits.max_decompressed_bytes:
                member.outcome = "budget_exceeded"
                member.diagnostic = "decompressed_bytes"
                budget_failed = True
                continue
            try:
                with archive.open(info, "r") as reader:
                    if extract_members:
                        member.artifact_path = _publish_reader(output_root, member.safe_name, reader, budget)
                        member.outcome = "extracted"
                    else:
                        for _ in _reader_chunks(reader):
                            pass
                        member.outcome = "validated"
            except BudgetExceeded:
                raise
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError) as exc:
                member.outcome = "checksum_or_method_failed"
                member.diagnostic = str(exc)
                continue
            total += info.file_size
        if budget_failed:
            outcome = "budget_exceeded"
        elif members and all(member.outcome in {"extracted", "validated", "directory"} for member in members):
            outcome = "validated_original"
        elif members:
            outcome = "partial"
        else:
            outcome = "failed"
        return ArchiveRecovery("zip", outcome, members)

    def _scan_zip_locals(self, data: bytes, limits: ResourceLimits) -> list[tuple[ArchiveMemberResult, bytes]]:
        results: list[tuple[ArchiveMemberResult, bytes]] = []
        cursor = 0
        total = 0
        while len(results) < limits.max_archive_members:
            offset = data.find(b"PK\x03\x04", cursor)
            if offset < 0 or offset + 30 > len(data):
                break
            try:
                _, _, flags, method, _, _, crc, compressed_size, uncompressed_size, name_len, extra_len = struct.unpack_from("<4s5H3I2H", data, offset)
            except struct.error:
                break
            header_end = offset + 30 + name_len + extra_len
            payload_end = header_end + compressed_size
            raw_name = data[offset + 30:offset + 30 + name_len]
            name = raw_name.decode("utf-8" if flags & 0x800 else "cp437", errors="replace")
            member = ArchiveMemberResult(name, _safe_name(name), offset, str(method), compressed_size, uncompressed_size, f"{crc:08x}", bool(flags & 1))
            payload = b""
            results.append((member, payload))
            cursor = max(offset + 4, payload_end)
            if flags & 1:
                member.outcome = "encrypted"
                continue
            if flags & 8 or compressed_size == 0 and uncompressed_size != 0:
                member.outcome = "ambiguous_descriptor"
                continue
            if member.safe_name is None:
                member.outcome = "unsafe_path"
                continue
            if payload_end > len(data):
                member.outcome = "truncated_member"
                continue
            compressed = data[header_end:payload_end]
            if _ratio_exceeded(compressed_size, uncompressed_size, limits) or total + uncompressed_size > limits.max_decompressed_bytes:
                member.outcome = "budget_exceeded"
                continue
            try:
                payload = compressed if method == 0 else zlib.decompress(compressed, -15) if method == 8 else b""
            except zlib.error as exc:
                member.outcome = "decompression_failed"
                member.diagnostic = str(exc)
                continue
            if method not in {0, 8}:
                member.outcome = "unsupported_method"
                continue
            if len(payload) != uncompressed_size or (binascii.crc32(payload) & 0xFFFFFFFF) != crc:
                member.outcome = "checksum_failed"
                continue
            member.outcome = "validated"
            total += len(payload)
            results[-1] = (member, payload)
        return results

    def _recover_tar(self, data: bytes, output_root: Path | None, limits: ResourceLimits, budget: BudgetTracker | None, extract_members: bool, publish_repair: bool) -> ArchiveRecovery:
        members: list[ArchiveMemberResult] = []
        recovered: list[tuple[ArchiveMemberResult, bytes]] = []
        structural_damage = False
        skipped_blocks = 0
        total = 0
        offset = 0
        while offset + 512 <= len(data) and len(members) < limits.max_archive_members:
            header = data[offset:offset + 512]
            if header == b"\0" * 512:
                offset += 512
                continue
            checksum_field = header[148:156]
            try:
                expected = int(checksum_field.rstrip(b"\0 ") or b"0", 8)
            except ValueError:
                structural_damage = True
                skipped_blocks += 1
                offset += 512
                continue
            actual = sum(header[:148]) + (32 * 8) + sum(header[156:])
            if actual != expected:
                structural_damage = True
                skipped_blocks += 1
                offset += 512
                continue
            name = header[:100].split(b"\0", 1)[0].decode("utf-8", errors="replace")
            try:
                size = int(header[124:136].rstrip(b"\0 ") or b"0", 8)
            except ValueError:
                size = 0
            typeflag = header[156:157] or b"0"
            data_start = offset + 512
            data_end = data_start + size
            member = ArchiveMemberResult(name, _safe_name(name), offset, "tar", size, size, f"{expected:o}")
            members.append(member)
            next_offset = data_start + ((size + 511) // 512) * 512
            if member.safe_name is None:
                member.outcome = "unsafe_path"
            elif typeflag not in {b"0", b"\0", b"5"}:
                member.outcome = "link_or_device_rejected"
            elif typeflag == b"5":
                member.outcome = "directory"
            elif data_end > len(data):
                member.outcome = "truncated_member"
                structural_damage = True
            elif size > limits.max_archive_member_bytes or total + size > limits.max_decompressed_bytes:
                member.outcome = "budget_exceeded"
            else:
                payload = data[data_start:data_end]
                try:
                    if extract_members:
                        member.artifact_path = _publish(output_root, member.safe_name, payload, budget)
                        member.outcome = "extracted"
                    else:
                        member.outcome = "validated"
                    recovered.append((member, payload))
                    total += size
                except BudgetExceeded:
                    raise
                except Exception as exc:
                    member.outcome = "publication_failed"
                    member.diagnostic = str(exc)
            offset = max(offset + 512, next_offset)
        rebuilt = None
        if recovered and structural_damage:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w") as target:
                for member, payload in recovered:
                    info = tarfile.TarInfo(member.safe_name or member.original_name)
                    info.size = len(payload)
                    info.mtime = 0
                    target.addfile(info, io.BytesIO(payload))
            rebuilt = buffer.getvalue()
            if output_root is not None and publish_repair:
                _publish(output_root, "repaired.tar", rebuilt, budget)
        if any(member.outcome == "budget_exceeded" for member in members):
            outcome = "budget_exceeded"
        elif members and all(member.outcome in {"extracted", "validated", "directory"} for member in members):
            outcome = "validated_original"
        elif recovered:
            outcome = "partial"
        else:
            outcome = "failed"
        diagnostics = []
        if structural_damage:
            diagnostics.append({"tar_resynchronization": {"skipped_blocks": skipped_blocks}})
        return ArchiveRecovery("tar", outcome, members, rebuilt, diagnostics)

    def _recover_open_tar(
        self,
        archive: tarfile.TarFile,
        output_root: Path | None,
        limits: ResourceLimits,
        budget: BudgetTracker | None,
        extract_members: bool,
    ) -> ArchiveRecovery:
        """Validate/extract a seekable TAR while keeping member payloads streamed."""
        infos: list[tarfile.TarInfo] = []
        member_limit_exceeded = False
        for info in archive:
            if len(infos) >= limits.max_archive_members:
                member_limit_exceeded = True
                break
            infos.append(info)

        members: list[ArchiveMemberResult] = []
        names: set[str] = set()
        total = 0
        for info in sorted(infos, key=lambda item: (item.name.casefold(), item.offset)):
            safe_name = _safe_name(info.name)
            member = ArchiveMemberResult(
                info.name,
                safe_name,
                int(info.offset),
                "tar",
                int(info.size),
                int(info.size),
                None,
            )
            members.append(member)
            if safe_name is None:
                member.outcome = "unsafe_path"
                continue
            if safe_name in names:
                member.outcome = "duplicate_rejected"
                continue
            names.add(safe_name)
            if info.issym() or info.islnk() or info.isdev():
                member.outcome = "link_or_device_rejected"
                continue
            if info.isdir():
                member.outcome = "directory"
                continue
            if not info.isfile():
                member.outcome = "unsupported_member_type"
                continue
            if info.size > limits.max_archive_member_bytes or total + info.size > limits.max_decompressed_bytes:
                member.outcome = "budget_exceeded"
                member.diagnostic = "member_size_or_decompressed_bytes"
                continue
            reader = archive.extractfile(info)
            if reader is None:
                member.outcome = "unreadable"
                continue
            try:
                with reader:
                    if extract_members:
                        member.artifact_path = _publish_reader(output_root, safe_name, reader, budget)
                        member.outcome = "extracted"
                    else:
                        for _ in _reader_chunks(reader):
                            pass
                        member.outcome = "validated"
            except BudgetExceeded:
                raise
            except (tarfile.TarError, OSError) as exc:
                member.outcome = "unreadable"
                member.diagnostic = str(exc)
                continue
            total += info.size

        diagnostics = [{"budget": "archive_members"}] if member_limit_exceeded else []
        if member_limit_exceeded or any(member.outcome == "budget_exceeded" for member in members):
            outcome = "budget_exceeded"
        elif members and all(member.outcome in {"extracted", "validated", "directory"} for member in members):
            outcome = "validated_original"
        elif members:
            outcome = "partial"
        else:
            outcome = "failed"
        return ArchiveRecovery("tar", outcome, members, diagnostics=diagnostics)

    def recover_source(
        self,
        source: FileByteSource,
        *,
        suffix: str,
        output_root: Path | None = None,
        limits: ResourceLimits | None = None,
        depth: int = 0,
        budget: BudgetTracker | None = None,
        goal: str | None = None,
    ) -> ArchiveRecovery:
        """Prefer streaming container parsers and bound damaged-file fallback."""
        limits = limits or ResourceLimits()
        extract_members = goal is None or goal in {RecoveryGoal.EXTRACT.value, RecoveryGoal.CARVE.value}
        if depth > limits.max_nesting_depth:
            return ArchiveRecovery("unknown", "budget_exceeded", diagnostics=[{"budget": "nesting_depth"}])
        source.assert_unchanged()
        is_tar = suffix.lower() == ".tar"
        if not is_tar and source.size >= 262:
            is_tar = source.read(257, 5) == b"ustar"
        try:
            with source.open_reader() as reader:
                if is_tar:
                    with tarfile.open(fileobj=reader, mode="r:*") as archive:
                        result = self._recover_open_tar(archive, output_root, limits, budget, extract_members)
                else:
                    with zipfile.ZipFile(reader) as archive:
                        result = self._recover_open_zip(
                            archive,
                            archive.infolist(),
                            output_root,
                            limits,
                            budget,
                            extract_members,
                        )
            source.assert_unchanged()
            return result
        except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError) as exc:
            if source.size > limits.max_materialized_bytes:
                return ArchiveRecovery(
                    "tar" if is_tar else "zip",
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
                depth=depth,
                budget=budget,
                goal=goal,
            )

    def inspect(self, context: HandlerContext) -> InspectionResult:
        result = self.recover_source(context.source, suffix=context.record.path.suffix, limits=context.limits)
        return InspectionResult("archive", result.outcome not in {"failed", "budget_exceeded"}, 0.95 if result.outcome == "validated_original" else 0.7, diagnostics=result.diagnostics, parts=[asdict(member) for member in result.members])

    def plan(self, context: HandlerContext, goal: RecoveryGoal) -> list[CandidatePlan]:
        if goal not in {RecoveryGoal.REPAIR, RecoveryGoal.EXTRACT, RecoveryGoal.CARVE}:
            return []
        return [CandidatePlan(f"{self.handler_id}:{goal.value}", self.handler_id, goal.value, "archive", goal.value, 100, (), estimated_materialized_bytes=0, estimated_output_bytes=context.source.size, meta={"source_mode": "stream", "fallback_materialization_limit": context.limits.max_materialized_bytes})]

    def execute(self, context: HandlerContext, plan: CandidatePlan) -> RecoveryOutcome:
        result = self.recover_source(
            context.source,
            suffix=context.record.path.suffix,
            output_root=context.output_root,
            limits=context.limits,
            budget=context.budget,
            goal=plan.goal,
        )
        ok = result.outcome not in {"failed", "budget_exceeded"}
        grade = OutcomeGrade.VALIDATED_ORIGINAL.value if result.outcome == "validated_original" else OutcomeGrade.PARTIAL_CONTENT.value if ok else OutcomeGrade.BUDGET_EXCEEDED.value if result.outcome == "budget_exceeded" else OutcomeGrade.FAILED.value
        return RecoveryOutcome(None, DecodeResult(ok=ok, decoder=self.handler_id, telemetry={"format": result.format, "outcome": result.outcome, "members": [asdict(member) for member in result.members]}), grade=grade, diagnostics=result.diagnostics)
