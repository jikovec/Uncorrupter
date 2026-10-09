from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from file_uncorrupter.handlers.pdf import PDFHandler


def simple_pdf() -> bytes:
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Length 35 >>\nstream\nBT (Recovered PDF text) Tj ET\nendstream\nendobj\n",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for item in objects:
        offsets.append(len(data))
        data.extend(item)
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def test_valid_pdf_structure_pages_streams_and_text_are_inspected(tmp_path):
    result = PDFHandler().recover_bytes(simple_pdf(), output_root=tmp_path)

    assert result.outcome == "validated_original"
    assert result.object_count == 4
    assert result.page_count == 1
    assert "Recovered PDF text" in result.text
    assert result.xref_valid is True
    assert any(path.name == "extracted-text.txt" for path in result.artifacts)


def test_prefixed_missing_eof_and_broken_startxref_are_repaired_conservatively(tmp_path):
    broken = b"garbage-prefix" + simple_pdf().replace(b"startxref\n", b"startxref\n999999\n% old ", 1).replace(b"%%EOF\n", b"")
    result = PDFHandler().recover_bytes(broken, output_root=tmp_path)

    assert result.outcome == "repaired"
    assert result.prefix_bytes == len(b"garbage-prefix")
    assert result.rebuilt_bytes is not None
    assert result.rebuilt_bytes.startswith(b"%PDF-")
    assert result.rebuilt_bytes.rstrip().endswith(b"%%EOF")
    repaired_check = PDFHandler().analyze_bytes(result.rebuilt_bytes)
    assert repaired_check.xref_valid is True


def test_missing_xref_and_orphan_objects_are_reindexed_without_inventing_pages():
    data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n9 0 obj\n(Orphan)\nendobj\n%%EOF\n"
    result = PDFHandler().recover_bytes(data)

    assert result.outcome == "repaired"
    assert result.object_count == 2
    assert result.page_count == 0
    assert result.rebuilt_bytes is not None
    assert b"xref" in result.rebuilt_bytes


def test_encrypted_pdf_is_reported_without_repair_or_content_claims():
    encrypted = simple_pdf().replace(b"<< /Size 5 /Root 1 0 R >>", b"<< /Size 5 /Root 1 0 R /Encrypt 8 0 R >>")
    result = PDFHandler().recover_bytes(encrypted)

    assert result.encrypted is True
    assert result.outcome == "encrypted"
    assert result.rebuilt_bytes is None


def test_optional_qpdf_absence_is_explicit_not_a_native_failure():
    result = PDFHandler().recover_bytes(simple_pdf(), use_qpdf=True, qpdf_path="definitely-missing-qpdf")

    assert result.outcome == "validated_original"
    assert result.tool_evidence["available"] is False
    assert result.tool_evidence["error"] == "not_found"


def test_qpdf_repair_output_is_exactly_validated_and_atomically_published(tmp_path, monkeypatch):
    qpdf_path = tmp_path / "qpdf"
    qpdf_path.write_bytes(b"fake")

    def fake_probe(*_args, **_kwargs):
        return SimpleNamespace(
            available=True,
            resolved_path=str(qpdf_path),
            version="qpdf fake 1.0",
            error=None,
        )

    def fake_run(command, _policy, *, cancellation=None):
        if "--check" not in command:
            source_path = Path(command[-2])
            output_path = Path(command[-1])
            source = source_path.read_bytes()
            rewritten = source.replace(b"%%EOF", b"% qpdf-rewritten\n%%EOF")
            output_path.write_bytes(rewritten)
        empty_hash = hashlib.sha256(b"").hexdigest()
        return SimpleNamespace(
            returncode=0,
            stdout=b"",
            stderr=b"",
            stdout_sha256=empty_hash,
            stderr_sha256=empty_hash,
            timed_out=False,
            cancelled=False,
            output_truncated=False,
            duration_seconds=0.01,
            cleanup_ok=True,
        )

    monkeypatch.setattr("file_uncorrupter.handlers.pdf.probe_tool", fake_probe)
    monkeypatch.setattr("file_uncorrupter.handlers.pdf.run_process", fake_run)
    broken = simple_pdf().replace(b"startxref\n", b"startxref\n999999\n% old ", 1).replace(b"%%EOF\n", b"")

    result = PDFHandler().recover_bytes(
        broken,
        output_root=tmp_path / "output",
        use_qpdf=True,
        qpdf_path=str(qpdf_path),
        goal="repair",
    )

    assert result.outcome == "repaired"
    assert result.xref_valid is True
    assert result.tool_evidence["validated"] is True
    assert [item["operation"] for item in result.tool_evidence["runs"]] == ["repair", "check"]
    repaired = tmp_path / "output" / "repaired.pdf"
    assert repaired.read_bytes() == result.rebuilt_bytes
    assert b"qpdf-rewritten" in repaired.read_bytes()
