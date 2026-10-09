from __future__ import annotations

from pathlib import Path

from file_uncorrupter.capabilities import build_capability_manifest, capability_json, capability_markdown, validate_capability_manifest
from file_uncorrupter.classification import classify_record
from file_uncorrupter.handlers.registry import build_handler_registry
from file_uncorrupter.intake import build_file_record

import io
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def test_capability_manifest_is_deterministic_complete_and_passes_quality_gate(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    first = capability_json()
    second = capability_json()
    manifest = build_capability_manifest()

    assert first == second
    assert manifest["quality_gate"] == {"passed": True, "errors": []}
    variants = {variant for record in manifest["capabilities"] for variant in record["variants"]}
    assert {
        "jpeg", "png", "gif", "tiff", "avif", "mp4", "mkv", "wav", "mp3",
        "txt", "markdown", "zip", "tar", "docx", "xlsx", "pptx", "odt", "pdf", "7z", "rar", "rtf",
    } <= variants


def test_every_advertised_operation_has_fixture_evidence(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    manifest = build_capability_manifest()

    for record in manifest["capabilities"]:
        if any(level != "none" for level in record["operations"].values()):
            assert record["fixtures"], record["family"]
    assert validate_capability_manifest(manifest) == []


def test_variant_public_ownership_is_unique(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    registry = build_handler_registry()
    owners: dict[str, str] = {}
    for record in registry.capabilities():
        for variant in record.variants:
            assert variant not in owners, f"{variant}: {owners.get(variant)} and {record.handler_id}"
            owners[variant] = record.handler_id


def test_package_extension_and_zip_container_evidence_remain_distinct(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    path = tmp_path / "document.docx"
    path.write_bytes(buffer.getvalue())
    record = build_file_record(tmp_path, path, buffer.getvalue())
    classification = classify_record(record, buffer.getvalue())

    assert record.declared_kind == "docx"
    assert record.byte0_kind == "zip"
    assert classification.family == "docx"
    assert classification.evidence["extension_evidence"]["declared_kind"] == "docx"
    assert classification.evidence["signature_evidence"]["byte0_kind"] == "zip"


def test_generated_capability_document_has_no_drift(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")

    assert (ROOT / "docs" / "capabilities.generated.md").read_text(encoding="utf-8") == capability_markdown()
