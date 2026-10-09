from __future__ import annotations

import io
import json
import struct
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from mutations import CORE_MUTATION_CLASSES, MutationCase, evidence_mutation_matrix


@dataclass(frozen=True, slots=True)
class FormatEvidenceFixture:
    family: str
    variant: str
    suffix: str
    cases: tuple[MutationCase, ...]

    @property
    def mutation_classes(self) -> frozenset[str]:
        return frozenset(case.name for case in self.cases)


def image_bytes(fmt: str, *, size: tuple[int, int] = (24, 18), frames: int = 1) -> bytes:
    images = [Image.new("RGB", size, (40 + index * 20, 80, 120)) for index in range(frames)]
    buffer = io.BytesIO()
    kwargs: dict[str, object] = {}
    if frames > 1 and fmt.upper() in {"GIF", "TIFF", "WEBP"}:
        kwargs.update(save_all=True, append_images=images[1:], duration=50, loop=0)
    images[0].save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def jpeg_bytes() -> bytes:
    return image_bytes("JPEG")


def png_bytes() -> bytes:
    return image_bytes("PNG")


def gif_bytes(*, frames: int = 1) -> bytes:
    return image_bytes("GIF", frames=frames)


def bmp_bytes() -> bytes:
    return image_bytes("BMP")


def tiff_bytes(*, frames: int = 1) -> bytes:
    return image_bytes("TIFF", frames=frames)


def webp_bytes(*, frames: int = 1) -> bytes:
    return image_bytes("WEBP", frames=frames)


def zip_bytes(members: dict[str, bytes], *, compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for name, payload in members.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = compression
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            archive.writestr(info, payload)
    return buffer.getvalue()


def tar_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mtime = 0
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def wav_bytes() -> bytes:
    samples = b"\x00\x00" * 32
    fmt = struct.pack("<HHIIHH", 1, 1, 8_000, 16_000, 2, 16)
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(samples)) + samples
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WAVE" + body


def mp4_bytes() -> bytes:
    def box(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I4s", len(payload) + 8, kind) + payload

    return box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2") + box(b"moov", b"") + box(b"mdat", b"synthetic")


def isobmff_bytes(brand: bytes) -> bytes:
    def box(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I4s", len(payload) + 8, kind) + payload

    return box(b"ftyp", brand + b"\x00\x00\x00\x00" + brand) + box(b"mdat", b"synthetic")


def ebml_bytes(*, webm: bool = False) -> bytes:
    doc_type = b"webm" if webm else b"matroska"
    return b"\x1a\x45\xdf\xa3" + bytes([0x80 + len(doc_type)]) + doc_type + b"\x18\x53\x80\x67\x80"


def avi_bytes() -> bytes:
    body = b"AVI " + b"LIST" + (0).to_bytes(4, "little")
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def mpegts_bytes() -> bytes:
    packets = []
    for continuity in range(5):
        packets.append(bytes([0x47, 0x01, 0x00, 0x10 | continuity]) + b"\xff" * 184)
    return b"".join(packets)


def openxml_bytes(variant: str) -> bytes:
    base = {"docm": "docx", "xlsm": "xlsx", "pptm": "pptx"}.get(variant, variant)
    main_parts = {
        "docx": ("word/document.xml", "document"),
        "xlsx": ("xl/workbook.xml", "workbook"),
        "pptx": ("ppt/presentation.xml", "presentation"),
    }
    main_part, root_name = main_parts[base]
    macro = variant.endswith("m")
    members = {
        "[Content_Types].xml": b'<?xml version="1.0"?><Types/>',
        "_rels/.rels": b'<?xml version="1.0"?><Relationships/>',
        main_part: f'<?xml version="1.0"?><{root_name}><text>Synthetic {variant}</text></{root_name}>'.encode(),
    }
    if macro:
        members[f"{main_part.split('/', 1)[0]}/vbaProject.bin"] = b"VBA synthetic inert fixture"
    return zip_bytes(members)


def odf_bytes(variant: str) -> bytes:
    media_type = {
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "odp": "application/vnd.oasis.opendocument.presentation",
    }[variant]
    return zip_bytes(
        {
            "mimetype": media_type.encode("ascii"),
            "META-INF/manifest.xml": b'<?xml version="1.0"?><manifest/>',
            "content.xml": f'<?xml version="1.0"?><content><text>Synthetic {variant}</text></content>'.encode(),
        },
        compression=zipfile.ZIP_STORED,
    )


def rtf_bytes() -> bytes:
    return br"{\rtf1\ansi Synthetic recovery fixture.}"


def seven_zip_header_bytes() -> bytes:
    return b"7z\xbc\xaf'\x1c" + (b"\0" * 26)


def ole_header_bytes() -> bytes:
    return bytes.fromhex("d0cf11e0a1b11ae1") + (b"\0" * 504)


def docx_bytes(text: str = "Recovered document") -> bytes:
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        '</Relationships>'
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
    )
    return zip_bytes(
        {
            "[Content_Types].xml": content_types.encode(),
            "_rels/.rels": relationships.encode(),
            "word/document.xml": document.encode(),
        }
    )


def odt_bytes(text: str = "Recovered ODF") -> bytes:
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
        '<manifest:file-entry manifest:full-path="/" '
        'manifest:media-type="application/vnd.oasis.opendocument.text"/>'
        '</manifest:manifest>'
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        f'<office:body><office:text><text:p>{text}</text:p></office:text></office:body>'
        '</office:document-content>'
    )
    return zip_bytes(
        {
            "mimetype": b"application/vnd.oasis.opendocument.text",
            "META-INF/manifest.xml": manifest.encode(),
            "content.xml": content.encode(),
        },
        compression=zipfile.ZIP_STORED,
    )


def simple_pdf_bytes(text: str = "Recovered PDF") -> bytes:
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n",
    ]
    stream = f"BT ({text}) Tj ET".encode("latin-1")
    objects.append(
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n"
    )
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(output))
        output.extend(obj)
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def format_evidence_inventory() -> tuple[FormatEvidenceFixture, ...]:
    """Return license-safe synthetic evidence for every public capability family."""

    archive = zip_bytes({"safe.txt": b"safe"})
    archive_index = archive.find(b"PK\x01\x02")
    archive_oversized = bytearray(archive)
    archive_oversized[archive_index + 24:archive_index + 28] = (0x7FFFFFFF).to_bytes(4, "little")
    package = docx_bytes()
    package_index = package.find(b"PK\x01\x02")
    pdf = simple_pdf_bytes()
    pdf_xref = pdf.find(b"xref\n")
    png = png_bytes()
    png_oversized = bytearray(png)
    png_oversized[8:12] = (0x7FFFFFFF).to_bytes(4, "big")
    media = mp4_bytes()
    media_missing_index = media.replace(struct.pack(">I4s", 8, b"moov"), b"")

    fixtures = [
        FormatEvidenceFixture(
            "archive",
            "zip",
            ".zip",
            evidence_mutation_matrix(
                archive,
                suffix=".zip",
                missing_index=archive[:archive_index],
                oversized_declaration=bytes(archive_oversized),
                path_attack=zip_bytes({"../escape.txt": b"blocked"}),
                resource_attack=zip_bytes({"expand.txt": b"A" * 100_000}),
            ),
        ),
        FormatEvidenceFixture("external_archive", "7z", ".7z", evidence_mutation_matrix(seven_zip_header_bytes(), suffix=".7z")),
        FormatEvidenceFixture("image", "png", ".png", evidence_mutation_matrix(png, suffix=".png", oversized_declaration=bytes(png_oversized))),
        FormatEvidenceFixture("jpeg", "jpeg", ".jpg", evidence_mutation_matrix(jpeg_bytes(), suffix=".jpg")),
        FormatEvidenceFixture("legacy_office", "doc", ".doc", evidence_mutation_matrix(ole_header_bytes(), suffix=".doc")),
        FormatEvidenceFixture("media", "mp4", ".mp4", evidence_mutation_matrix(media, suffix=".mp4", missing_index=media_missing_index)),
        FormatEvidenceFixture(
            "package_document",
            "docx",
            ".docx",
            evidence_mutation_matrix(
                package,
                suffix=".docx",
                missing_index=package[:package_index],
                path_attack=zip_bytes({"[Content_Types].xml": b"<Types/>", "../escape.bin": b"blocked"}),
                resource_attack=zip_bytes({"word/document.xml": b"A" * 100_000}),
            ),
        ),
        FormatEvidenceFixture("pdf", "pdf", ".pdf", evidence_mutation_matrix(pdf, suffix=".pdf", missing_index=pdf[:pdf_xref] + b"%%EOF\n")),
        FormatEvidenceFixture("rtf", "rtf", ".rtf", evidence_mutation_matrix(rtf_bytes(), suffix=".rtf")),
        FormatEvidenceFixture("text", "txt", ".txt", evidence_mutation_matrix(b"first\nsecond\n", suffix=".txt")),
    ]

    additional_specs = (
        ("archive", "tar", ".tar", tar_bytes({"safe.txt": b"safe"})),
        ("external_archive", "rar", ".rar", b"Rar!\x1a\x07\x01\x00" + b"\0" * 32),
        ("image", "gif", ".gif", gif_bytes()),
        ("image", "bmp", ".bmp", bmp_bytes()),
        ("image", "webp", ".webp", webp_bytes()),
        ("image", "tiff", ".tiff", tiff_bytes()),
        ("image", "heif", ".heic", isobmff_bytes(b"heic")),
        ("image", "avif", ".avif", isobmff_bytes(b"avif")),
        ("image", "jp2", ".jp2", b"\x00\x00\x00\x0cjP  \r\n\x87\n" + isobmff_bytes(b"jp2 ")),
        ("image", "raw", ".dng", tiff_bytes()),
        ("legacy_office", "xls", ".xls", ole_header_bytes()),
        ("legacy_office", "ppt", ".ppt", ole_header_bytes()),
        ("media", "mov", ".mov", isobmff_bytes(b"qt  ")),
        ("media", "mkv", ".mkv", ebml_bytes()),
        ("media", "webm", ".webm", ebml_bytes(webm=True)),
        ("media", "avi", ".avi", avi_bytes()),
        ("media", "mpegts", ".ts", mpegts_bytes()),
        ("media", "mpegps", ".mpg", b"\x00\x00\x01\xba" + b"\0" * 64),
        ("media", "flv", ".flv", b"FLV\x01\x05\x00\x00\x00\x09" + b"\0" * 16),
        ("media", "asf", ".asf", bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c") + b"\0" * 32),
        ("media", "wmv", ".wmv", bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c") + b"\0" * 32),
        ("media", "wav", ".wav", wav_bytes()),
        ("media", "mp3", ".mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00\xff\xfb\x90\x64"),
        ("media", "flac", ".flac", b"fLaC" + b"\0" * 32),
        ("media", "aac", ".aac", b"\xff\xf1\x50\x80\x00\x1f\xfc"),
        ("media", "ogg", ".ogg", b"OggS\x00" + b"\0" * 32),
        ("package_document", "docm", ".docm", openxml_bytes("docm")),
        ("package_document", "xlsx", ".xlsx", openxml_bytes("xlsx")),
        ("package_document", "xlsm", ".xlsm", openxml_bytes("xlsm")),
        ("package_document", "pptx", ".pptx", openxml_bytes("pptx")),
        ("package_document", "pptm", ".pptm", openxml_bytes("pptm")),
        ("package_document", "odt", ".odt", odf_bytes("odt")),
        ("package_document", "ods", ".ods", odf_bytes("ods")),
        ("package_document", "odp", ".odp", odf_bytes("odp")),
        ("text", "markdown", ".md", b"# Synthetic markdown\n"),
        ("text", "log", ".log", b"2026-08-08 INFO synthetic\n"),
        ("text", "csv", ".csv", b"name,value\nsynthetic,1\n"),
        ("text", "json", ".json", b'{"synthetic": true}\n'),
        ("text", "xml", ".xml", b'<?xml version="1.0"?><synthetic>true</synthetic>\n'),
        ("text", "html", ".html", b"<!doctype html><title>Synthetic</title>\n"),
    )
    fixtures.extend(
        FormatEvidenceFixture(family, variant, suffix, evidence_mutation_matrix(payload, suffix=suffix))
        for family, variant, suffix, payload in additional_specs
    )
    fixtures.sort(key=lambda fixture: (fixture.family, fixture.variant))
    assert all(CORE_MUTATION_CLASSES <= fixture.mutation_classes for fixture in fixtures)
    return tuple(fixtures)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
