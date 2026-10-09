from __future__ import annotations

import io
import zipfile

import pytest

from file_uncorrupter.handlers.package_document import PackageDocumentHandler


def package_bytes(kind: str, *, macro: bool = False, omit_required: bool = False) -> bytes:
    roots = {
        "docx": ("word/document.xml", "<w:document xmlns:w='w'><w:body><w:p><w:t>Document text</w:t></w:p></w:body></w:document>"),
        "xlsx": ("xl/workbook.xml", "<workbook><sheet>Sheet text</sheet></workbook>"),
        "pptx": ("ppt/presentation.xml", "<presentation><slide>Slide text</slide></presentation>"),
        "odt": ("content.xml", "<document><p>ODT text</p></document>"),
        "ods": ("content.xml", "<document><table>ODS text</table></document>"),
        "odp": ("content.xml", "<document><slide>ODP text</slide></document>"),
    }
    part, xml = roots[kind]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        if kind in {"docx", "xlsx", "pptx"}:
            if not omit_required:
                archive.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>")
            archive.writestr("_rels/.rels", "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'/>")
        else:
            mime = {"odt": "application/vnd.oasis.opendocument.text", "ods": "application/vnd.oasis.opendocument.spreadsheet", "odp": "application/vnd.oasis.opendocument.presentation"}[kind]
            archive.writestr("mimetype", mime)
            if not omit_required:
                archive.writestr("META-INF/manifest.xml", "<manifest/>")
        archive.writestr(part, xml)
        archive.writestr("media/image.bin", b"image")
        if macro:
            archive.writestr("word/vbaProject.bin", b"macro")
    return buffer.getvalue()


@pytest.mark.parametrize("kind", ["docx", "xlsx", "pptx", "odt", "ods", "odp"])
def test_package_types_validate_required_parts_and_extract_text(kind, tmp_path):
    result = PackageDocumentHandler().recover_bytes(package_bytes(kind), suffix=f".{kind}", output_root=tmp_path / kind)

    assert result.package_type == kind
    assert result.outcome == "validated_original"
    assert result.text
    assert any("text" in path.name for path in result.artifacts)


def test_package_missing_required_part_is_partial_not_full(tmp_path):
    result = PackageDocumentHandler().recover_bytes(
        package_bytes("docx", omit_required=True), suffix=".docx", output_root=tmp_path
    )

    assert result.outcome == "partial_content"
    assert "[Content_Types].xml" in result.missing_required
    assert result.text == "Document text"


def test_package_macros_and_active_content_are_reported_never_executed(tmp_path):
    result = PackageDocumentHandler().recover_bytes(package_bytes("docx", macro=True), suffix=".docm", output_root=tmp_path)

    assert result.macro_parts == ["word/vbaProject.bin"]
    assert result.active_content is True
    assert result.outcome == "validated_original"


def test_package_with_missing_zip_directory_uses_conservative_local_rebuild(tmp_path):
    original = package_bytes("docx")
    truncated = original[: original.find(b"PK\x01\x02")]
    result = PackageDocumentHandler().recover_bytes(truncated, suffix=".docx", output_root=tmp_path)

    assert result.outcome == "repaired_package"
    assert result.rebuilt_bytes is not None
    assert result.text == "Document text"
