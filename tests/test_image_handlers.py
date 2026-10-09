from __future__ import annotations

import binascii
import io

from PIL import Image

from file_uncorrupter.handlers.image import ImageHandler


def image_bytes(fmt: str, *, frames: int = 1) -> bytes:
    images = [Image.new("RGBA", (10, 7), (20 + index * 30, 40, 60, 255)) for index in range(frames)]
    buffer = io.BytesIO()
    kwargs = {"save_all": True, "append_images": images[1:], "duration": 20, "loop": 0} if frames > 1 else {}
    images[0].save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def corrupt_first_png_crc(data: bytes) -> bytes:
    damaged = bytearray(data)
    length = int.from_bytes(damaged[8:12], "big")
    crc_offset = 8 + 8 + length
    damaged[crc_offset:crc_offset + 4] = b"\x00\x00\x00\x00"
    return bytes(damaged)


def test_png_crc_and_missing_iend_are_repaired_with_valid_chunk_evidence(tmp_path):
    original = image_bytes("PNG")
    damaged = corrupt_first_png_crc(original[:-12])
    result = ImageHandler().recover_bytes(damaged, suffix=".png", output_root=tmp_path)

    assert result.family == "png"
    assert result.outcome == "repaired"
    assert result.rebuilt_bytes is not None
    assert result.diagnostics["crc_repairs"] >= 1
    assert result.diagnostics["iend_appended"] is True
    with Image.open(io.BytesIO(result.rebuilt_bytes)) as image:
        image.load()
        assert image.size == (10, 7)


def test_gif_animation_is_preserved_and_missing_trailer_is_repaired(tmp_path):
    original = image_bytes("GIF", frames=2)
    result = ImageHandler().recover_bytes(original, suffix=".gif", output_root=tmp_path / "valid")
    assert result.outcome == "validated_original"
    assert result.frame_count == 2

    repaired = ImageHandler().recover_bytes(original[:-1], suffix=".gif", output_root=tmp_path / "repair")
    assert repaired.outcome == "repaired"
    assert repaired.rebuilt_bytes is not None and repaired.rebuilt_bytes.endswith(b";")


def test_bmp_declared_size_and_webp_riff_size_are_repaired():
    bmp = bytearray(image_bytes("BMP"))
    bmp[2:6] = (1).to_bytes(4, "little")
    bmp_result = ImageHandler().recover_bytes(bytes(bmp), suffix=".bmp")
    assert bmp_result.outcome == "repaired"
    assert int.from_bytes(bmp_result.rebuilt_bytes[2:6], "little") == len(bmp)

    webp = bytearray(image_bytes("WEBP"))
    webp[4:8] = (1).to_bytes(4, "little")
    webp_result = ImageHandler().recover_bytes(bytes(webp), suffix=".webp")
    assert webp_result.outcome == "repaired"
    assert int.from_bytes(webp_result.rebuilt_bytes[4:8], "little") == len(webp) - 8


def test_tiff_multipage_evidence_is_preserved():
    result = ImageHandler().recover_bytes(image_bytes("TIFF", frames=3), suffix=".tiff")

    assert result.outcome == "validated_original"
    assert result.page_count == 3
    assert result.frame_count == 3


def test_codec_dependent_formats_are_honest_when_decoder_is_unavailable():
    fake_avif = b"\x00\x00\x00\x18ftypavif" + b"\x00" * 32
    result = ImageHandler().recover_bytes(fake_avif, suffix=".avif")

    assert result.family == "avif"
    assert result.outcome in {"unavailable_dependency", "failed"}
    assert result.rebuilt_bytes is None
