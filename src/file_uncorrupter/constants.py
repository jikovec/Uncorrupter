from __future__ import annotations

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
SOS = b"\xff\xda"
DQT = b"\xff\xdb"
DHT = b"\xff\xc4"
APP0 = b"\xff\xe0"
APP1 = b"\xff\xe1"

JPEG_SOF_MARKERS = [
    b"\xff\xc0", b"\xff\xc1", b"\xff\xc2", b"\xff\xc3",
    b"\xff\xc5", b"\xff\xc6", b"\xff\xc7",
    b"\xff\xc9", b"\xff\xca", b"\xff\xcb",
    b"\xff\xcd", b"\xff\xce", b"\xff\xcf",
]

PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_IHDR = b"IHDR"
PNG_IDAT = b"IDAT"
PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"

GIF87A = b"GIF87a"
GIF89A = b"GIF89a"
BMP_SIG = b"BM"
TIFF_LE = b"II*\x00"
TIFF_BE = b"MM\x00*"
RIFF = b"RIFF"
WEBP = b"WEBP"

ALL_KINDS = ["jpeg", "png", "gif", "bmp", "tiff", "webp"]

EXT_TO_KIND = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".jpe": "jpeg",
    ".jfif": "jpeg",
    ".png": "png",
    ".gif": "gif",
    ".bmp": "bmp",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".webp": "webp",
}

KIND_TO_PIL_FORMAT = {
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "bmp": "BMP",
    "tiff": "TIFF",
    "webp": "WEBP",
}
