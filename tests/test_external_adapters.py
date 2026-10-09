from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from file_uncorrupter.handlers.external import ExternalAdapterHandler, parse_7z_listing


def test_7z_listing_parses_encryption_solid_and_multivolume_boundaries():
    listing = """
Path = archive.7z
Type = 7z
Solid = +
Volumes = 2

----------
Path = folder/file.txt
Size = 12
Packed Size = 8
Attributes = A
Encrypted = +
"""
    parsed = parse_7z_listing(listing)

    assert parsed["solid"] is True
    assert parsed["volumes"] == 2
    assert parsed["members"][0]["path"] == "folder/file.txt"
    assert parsed["members"][0]["encrypted"] is True


def test_7z_and_rar_absent_tool_outcomes_are_explicit(tmp_path):
    archive = tmp_path / "sample.7z"
    archive.write_bytes(b"7z\xbc\xaf'\x1c" + b"\x00" * 32)
    result = ExternalAdapterHandler().inspect_archive(archive, tool="definitely-missing-7z")

    assert result.outcome == "unavailable_dependency"
    assert result.tool_evidence["available"] is False
    assert result.members == []


def test_rtf_text_is_recovered_without_executing_objects():
    payload = br"{\rtf1\ansi Hello \b recovered\b0 text\par second line {\object hidden}}"
    result = ExternalAdapterHandler().inspect_legacy_document(payload, suffix=".rtf")

    assert result.family == "rtf"
    assert "Hello" in result.text
    assert "recovered" in result.text
    assert result.active_content is True
    assert result.outcome == "partial_content"


def test_legacy_ole_macro_signal_is_reported_without_conversion():
    payload = bytes.fromhex("d0cf11e0a1b11ae1") + b"random VBA project bytes"
    result = ExternalAdapterHandler().inspect_legacy_document(payload, suffix=".doc", converter="missing-libreoffice")

    assert result.family == "legacy-office"
    assert result.macro is True
    assert result.active_content is True
    assert result.outcome == "unavailable_dependency"
    assert result.tool_evidence["available"] is False


def test_legacy_office_default_resolves_windows_soffice_alias(monkeypatch):
    calls: list[str] = []

    def fake_probe(executable, *_args, **_kwargs):
        calls.append(executable)
        available = executable == "soffice"
        return SimpleNamespace(
            name=executable,
            available=available,
            resolved_path="C:/Program Files/LibreOffice/program/soffice.exe" if available else None,
            version="LibreOffice fake 1.0" if available else None,
            error=None if available else "not_found",
        )

    monkeypatch.setattr("file_uncorrupter.handlers.external.probe_tool", fake_probe)
    payload = bytes.fromhex("d0cf11e0a1b11ae1") + b"legacy document"

    result = ExternalAdapterHandler().inspect_legacy_document(payload, suffix=".doc")

    assert calls == ["libreoffice", "soffice"]
    assert result.outcome == "partial_content"
    assert result.tool_evidence["executable_name"] == "soffice"


def _valid_pdf() -> bytes:
    objects = [b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"]
    data = bytearray(b"%PDF-1.4\n")
    offset = len(data)
    data.extend(objects[0])
    xref = len(data)
    data.extend(b"xref\n0 2\n0000000000 65535 f \n")
    data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def test_legacy_office_converter_publishes_only_a_validated_inert_pdf_preview(tmp_path, monkeypatch):
    def fake_probe(*_args, **_kwargs):
        return SimpleNamespace(
            available=True,
            resolved_path="fake-libreoffice",
            version="LibreOffice fake 1.0",
            error=None,
        )

    def fake_run(command, _policy, *, cancellation=None):
        output_root = Path(command[command.index("--outdir") + 1])
        output_root.joinpath("input.pdf").write_bytes(_valid_pdf())
        empty = hashlib.sha256(b"").hexdigest()
        return SimpleNamespace(
            returncode=0,
            stdout=b"",
            stderr=b"",
            stdout_sha256=empty,
            stderr_sha256=empty,
            timed_out=False,
            cancelled=False,
            output_truncated=False,
            duration_seconds=0.01,
            cleanup_ok=True,
        )

    monkeypatch.setattr("file_uncorrupter.handlers.external.probe_tool", fake_probe)
    monkeypatch.setattr("file_uncorrupter.handlers.external.run_process", fake_run)
    payload = bytes.fromhex("d0cf11e0a1b11ae1") + b"random VBA project bytes"

    result = ExternalAdapterHandler().convert_legacy_document(
        payload,
        suffix=".doc",
        output_root=tmp_path / "output",
    )

    assert result.outcome == "preview_only"
    assert result.converted_path == tmp_path / "output" / "preview.pdf"
    assert result.converted_path.read_bytes() == _valid_pdf()
    assert result.macro is True
    assert result.active_content is True
    assert result.tool_evidence["validation"]["passed"] is True
    assert result.tool_evidence["published_sha256"] == hashlib.sha256(_valid_pdf()).hexdigest()


def test_legacy_office_converter_rejects_invalid_pdf_before_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "file_uncorrupter.handlers.external.probe_tool",
        lambda *_args, **_kwargs: SimpleNamespace(
            available=True,
            resolved_path="fake-libreoffice",
            version="LibreOffice fake 1.0",
            error=None,
        ),
    )

    def fake_run(command, _policy, *, cancellation=None):
        output_root = Path(command[command.index("--outdir") + 1])
        output_root.joinpath("input.pdf").write_bytes(b"not a pdf")
        empty = hashlib.sha256(b"").hexdigest()
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"", stdout_sha256=empty, stderr_sha256=empty, timed_out=False, cancelled=False, output_truncated=False, duration_seconds=0.01, cleanup_ok=True)

    monkeypatch.setattr("file_uncorrupter.handlers.external.run_process", fake_run)
    result = ExternalAdapterHandler().convert_legacy_document(
        bytes.fromhex("d0cf11e0a1b11ae1") + b"document",
        suffix=".xls",
        output_root=tmp_path / "output",
    )

    assert result.outcome == "failed"
    assert result.tool_evidence["error"] == "converted_pdf_validation_failed"
    assert not (tmp_path / "output").exists() or not list((tmp_path / "output").glob("*"))
