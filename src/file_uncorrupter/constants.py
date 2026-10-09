from __future__ import annotations

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
SOS = b"\xff\xda"
DQT = b"\xff\xdb"
DHT = b"\xff\xc4"
DRI = b"\xff\xdd"
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
AVI = b"AVI "

EBML_HEADER = b"\x1A\x45\xDF\xA3"
FLV_SIG = b"FLV"
MPEG_PS_PACK = b"\x00\x00\x01\xBA"
JP2_SIG = b"\x00\x00\x00\x0cjP  \r\n\x87\n"
ASF_HEADER_GUID = bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")
ZIP_LOCAL = b"PK\x03\x04"
PDF_HEADER = b"%PDF-"
OLE_CFB = bytes.fromhex("d0cf11e0a1b11ae1")
SEVEN_Z = bytes.fromhex("377abcaf271c")
RAR4 = b"Rar!\x1a\x07\x00"
RAR5 = b"Rar!\x1a\x07\x01\x00"
FLAC = b"fLaC"
OGG = b"OggS"
ID3 = b"ID3"

IMAGE_KINDS = ["jpeg", "png", "gif", "bmp", "tiff", "webp", "heif", "avif", "jp2", "raw"]
VIDEO_KINDS = ["mp4", "mov", "avi", "mkv", "webm", "mpegts", "mpegps", "flv", "asf", "wmv"]
AUDIO_KINDS = ["wav", "mp3", "flac", "aac", "ogg"]
TEXT_KINDS = ["text", "markdown", "log", "csv", "json", "xml", "html"]
ARCHIVE_KINDS = ["zip", "tar", "7z", "rar"]
PACKAGE_KINDS = ["docx", "docm", "xlsx", "xlsm", "pptx", "pptm", "odt", "ods", "odp"]
DOCUMENT_KINDS = ["pdf", "rtf", "doc", "xls", "ppt"]
ALL_KINDS = IMAGE_KINDS + VIDEO_KINDS + AUDIO_KINDS + TEXT_KINDS + ARCHIVE_KINDS + PACKAGE_KINDS + DOCUMENT_KINDS

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
    ".heic": "heif",
    ".heif": "heif",
    ".avif": "avif",
    ".jp2": "jp2",
    ".j2k": "jp2",
    ".jpf": "jp2",
    ".jpx": "jp2",
    ".raw": "raw",
    ".dng": "raw",
    ".nef": "raw",
    ".cr2": "raw",
    ".cr3": "raw",
    ".arw": "raw",
    ".mp4": "mp4",
    ".m4v": "mp4",
    ".mov": "mov",
    ".avi": "avi",
    ".mkv": "mkv",
    ".webm": "webm",
    ".ts": "mpegts",
    ".m2ts": "mpegts",
    ".mts": "mpegts",
    ".mpg": "mpegps",
    ".mpeg": "mpegps",
    ".vob": "mpegps",
    ".flv": "flv",
    ".asf": "asf",
    ".wmv": "wmv",
    ".wav": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".aac": "aac",
    ".ogg": "ogg",
    ".oga": "ogg",
    ".txt": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".log": "log",
    ".csv": "csv",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".htm": "html",
    ".zip": "zip",
    ".tar": "tar",
    ".7z": "7z",
    ".rar": "rar",
    ".docx": "docx",
    ".docm": "docm",
    ".xlsx": "xlsx",
    ".xlsm": "xlsm",
    ".pptx": "pptx",
    ".pptm": "pptm",
    ".odt": "odt",
    ".ods": "ods",
    ".odp": "odp",
    ".pdf": "pdf",
    ".rtf": "rtf",
    ".doc": "doc",
    ".xls": "xls",
    ".ppt": "ppt",
}

KIND_TO_PIL_FORMAT = {
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "bmp": "BMP",
    "tiff": "TIFF",
    "webp": "WEBP",
}

IMAGE_OUTPUT_EXT = {
    "jpeg": ".jpg",
    "png": ".png",
    "gif": ".gif",
    "bmp": ".bmp",
    "tiff": ".tif",
    "webp": ".webp",
}

VIDEO_OUTPUT_EXT = {
    "mp4": ".mkv",
    "mov": ".mkv",
    "avi": ".mkv",
    "mkv": ".mkv",
    "webm": ".mkv",
    "mpegts": ".ts",
    "mpegps": ".mpg",
    "flv": ".mkv",
    "asf": ".mkv",
    "wmv": ".mkv",
}

ISOBMFF_BRANDS_TO_KIND = {
    b"isom": "mp4",
    b"iso2": "mp4",
    b"mp41": "mp4",
    b"mp42": "mp4",
    b"avc1": "mp4",
    b"dash": "mp4",
    b"qt  ": "mov",
    b"heic": "heif",
    b"heix": "heif",
    b"hevc": "heif",
    b"hevx": "heif",
    b"mif1": "heif",
    b"msf1": "heif",
    b"avif": "avif",
    b"avis": "avif",
    b"jp2 ": "jp2",
    b"jpx ": "jp2",
    b"jph ": "jp2",
}
