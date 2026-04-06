#!/usr/bin/env python3
"""
Aggressive damaged-image recovery with extension-first policy and deep diagnostics.

USER RULE IMPLEMENTED
---------------------
1. If the original file is named *.jpg / *.jpeg / *.png / *.gif / *.bmp / *.tif / *.tiff / *.webp,
   then that extension is treated as the authoritative intended format for recovery.
   Example:
       - A01.jpg  -> recover ONLY as JPEG
       - x.png    -> recover ONLY as PNG
2. Only when the file has:
       - no recognized image extension
       - and no recognizable header at byte 0
   do we try all supported formats.

WHY THIS SCRIPT EXISTS
----------------------
The previous runs showed:
- many files did not have a valid byte-0 signature,
- only a small number were recovered,
- most failures were "no_candidate_succeeded",
which strongly suggests the main problem is candidate generation / carving strategy:
we are not yet generating the right byte ranges for the decoder to salvage.

This version therefore focuses on:
- richer candidate generation
- detailed per-file diagnostics
- exact logging of what was tried and why it failed
- automatic summary recommendations for future changes

SUPPORTED DECLARED / INTENDED FORMATS
-------------------------------------
- JPEG / JPG / JPE / JFIF
- PNG
- GIF
- BMP
- TIFF / TIF
- WEBP

IMPORTANT OUTPUT BEHAVIOR
-------------------------
- Recovered files are written into a separate output folder.
- Original filenames are preserved.
- If the input file has a recognized extension, the recovered output uses the same filename and extension.
- If the input file has no recognized extension, the script writes a PNG by default.

EXAMPLES
--------
Windows PowerShell:
    python "F:\\Desktop\\New folder (3)\\a.py" ^
      "F:\\Desktop\\New folder (3)\\New folder" ^
      "F:\\Desktop\\New folder (3)\\New folder (2)" ^
      --recursive --no-ffmpeg ^
      --report-csv "F:\\Desktop\\New folder (3)\\recover_report.csv" ^
      --summary-json "F:\\Desktop\\New folder (3)\\recover_summary.json" ^
      --detail-jsonl "F:\\Desktop\\New folder (3)\\recover_detail.jsonl"

NOTES ABOUT LIMITATIONS
-----------------------
No decoder can reliably "ignore random corruption" in all image formats:

- JPEG:
  If enough tables / markers / stream continuity remain, decoders can often salvage partial output.
  If critical structure is gone, recovery may fail even if "a lot of bytes" still exist.

- PNG:
  PNG is much less tolerant. Damage in the compressed stream often breaks decompression state.

- GIF:
  Static first-frame recovery is easier than full animation recovery.

- BMP / TIFF:
  Can sometimes recover if the header / pixel offsets / strip data are mostly intact.

- WEBP:
  RIFF size fields and internal structure matter.

Still, because you believe the remaining image center is usually there, this script is built to:
- trust the intended format,
- carve internal candidates aggressively,
- and log exactly what needs improvement next.

"""

from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFile, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = True

# -----------------------------------------------------------------------------
# Format signatures / markers
# -----------------------------------------------------------------------------

SOI = b"\xff\xd8"  # JPEG start
EOI = b"\xff\xd9"  # JPEG end
SOS = b"\xff\xda"  # JPEG start of scan
DQT = b"\xff\xdb"  # JPEG quantization table
DHT = b"\xff\xc4"  # JPEG huffman table
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
GIF_TRAILER = b"\x3b"

BMP_SIG = b"BM"

TIFF_LE = b"II*\x00"
TIFF_BE = b"MM\x00*"

RIFF = b"RIFF"
WEBP = b"WEBP"

FFMPEG_PATH = shutil.which("ffmpeg")

# -----------------------------------------------------------------------------
# Kind / extension mappings
# -----------------------------------------------------------------------------

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

KIND_TO_EXT = {
    "jpeg": ".jpg",
    "png": ".png",
    "gif": ".gif",
    "bmp": ".bmp",
    "tiff": ".tif",
    "webp": ".webp",
}

KIND_TO_PIL_SAVE_FORMAT = {
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "bmp": "BMP",
    "tiff": "TIFF",
    "webp": "WEBP",
}

ALL_KINDS = ["jpeg", "png", "gif", "bmp", "tiff", "webp"]

# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    kind: str
    strategy: str
    start: int
    end: int | None
    prepend: bytes = b""
    append: bytes = b""
    priority: int = 0


@dataclass
class DecodeMeta:
    ok: bool
    width: int = 0
    height: int = 0
    mode: str = ""
    decoded_format: str = ""
    decoder: str = ""
    error: str = ""

    @property
    def area(self) -> int:
        return self.width * self.height


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def compact_error(text: str, max_lines: int = 4, max_chars: int = 400) -> str:
    """
    Normalize noisy decoder errors into something stable and readable.

    Why:
    - FFmpeg often returns many lines for one failure.
    - We want logs that remain useful without becoming unreadable.
    """
    text = (text or "").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""
    text = " | ".join(lines[:max_lines])
    if len(text) > max_chars:
        text = text[: max_chars - 3] + "..."
    return text


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read()


def find_all(data: bytes, needle: bytes, limit: int | None = None) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        if limit is not None and len(positions) >= limit:
            break
        start = idx + 1
    return positions


def sample_positions(positions: list[int], limit: int) -> list[int]:
    """
    Reduce a potentially huge marker list to a representative subset.

    Why:
    - Some corrupted files contain marker-like byte sequences everywhere.
    - Trying all positions is too expensive.
    - We keep edge positions + spread positions to preserve coverage.
    """
    if len(positions) <= limit:
        return positions[:]

    result: list[int] = []
    used: set[int] = set()

    anchors = [0, 1, 2, len(positions) - 3, len(positions) - 2, len(positions) - 1]
    for idx in anchors:
        if 0 <= idx < len(positions):
            p = positions[idx]
            if p not in used:
                used.add(p)
                result.append(p)

    remaining = limit - len(result)
    if remaining <= 0:
        return sorted(result)

    step = (len(positions) - 1) / max(1, remaining)
    for i in range(remaining):
        idx = round(i * step)
        p = positions[idx]
        if p not in used:
            used.add(p)
            result.append(p)

    return sorted(result)


def iter_files(folder: Path, recursive: bool, all_files: bool) -> Iterable[Path]:
    if all_files:
        iterator = folder.rglob("*") if recursive else folder.glob("*")
        for path in iterator:
            if path.is_file():
                yield path
        return

    iterator = folder.rglob("*") if recursive else folder.glob("*")
    for path in iterator:
        if path.is_file() and path.suffix.lower() in EXT_TO_KIND:
            yield path


def declared_kind_from_extension(path: Path) -> str | None:
    return EXT_TO_KIND.get(path.suffix.lower())


def header_kind_at_byte0(data: bytes) -> str:
    """
    Detect only by byte-0 header.

    Important:
    This is NOT used to override the user's extension rule.
    It is only for diagnostics, and for extension-less files.
    """
    if data.startswith(SOI):
        return "jpeg"
    if data.startswith(PNG_SIG):
        return "png"
    if data.startswith(GIF87A) or data.startswith(GIF89A):
        return "gif"
    if data.startswith(BMP_SIG):
        return "bmp"
    if data.startswith(TIFF_LE) or data.startswith(TIFF_BE):
        return "tiff"
    if data.startswith(RIFF) and len(data) >= 12 and data[8:12] == WEBP:
        return "webp"
    return "unknown"



def selected_kinds_for_file(path: Path, data: bytes) -> tuple[list[str], str]:
    """
    Primary selection policy.

    Pass 1:
    - trust the declared extension if present
    - else trust a valid byte-0 header if present
    - else try all kinds

    Pass 2 is handled later in recover_one():
    if pass 1 fails, we optionally try the remaining kinds as a fallback.
    """
    declared_kind = declared_kind_from_extension(path)
    if declared_kind:
        return [declared_kind], "extension_trusted"

    header_kind = header_kind_at_byte0(data)
    if header_kind != "unknown":
        return [header_kind], "header_used_no_extension"

    return ALL_KINDS[:], "no_extension_no_header_try_all"


def signature_positions_for_kind(data: bytes, kind: str, limit: int | None = None) -> list[int]:
    """
    Find strong format signatures anywhere in the blob.

    This is used only for ranking fallback kinds after the intended kind fails.
    """
    if kind == "jpeg":
        return find_all(data, SOI, limit)
    if kind == "png":
        return find_all(data, PNG_SIG, limit)
    if kind == "gif":
        return sorted(set(find_all(data, GIF87A, limit) + find_all(data, GIF89A, limit)))
    if kind == "bmp":
        return find_all(data, BMP_SIG, limit)
    if kind == "tiff":
        return sorted(set(find_all(data, TIFF_LE, limit) + find_all(data, TIFF_BE, limit)))
    if kind == "webp":
        riff_positions = find_all(data, RIFF)
        positions: list[int] = []
        for pos in riff_positions:
            if pos + 12 <= len(data) and data[pos + 8:pos + 12] == WEBP:
                positions.append(pos)
                if limit is not None and len(positions) >= limit:
                    break
        return positions
    return []


def anywhere_signature_hit_counts(data: bytes, sample_limit: int = 32) -> dict[str, int]:
    counts: dict[str, int] = {}
    for kind in ALL_KINDS:
        counts[kind] = len(signature_positions_for_kind(data, kind, sample_limit))
    return counts


def fallback_kinds_after_primary(primary_kinds: list[str], data: bytes, declared_kind: str | None) -> list[str]:
    """
    After the primary pass fails, rank the remaining kinds.

    Ranking logic:
    1. kinds with signatures found anywhere in the file first
    2. more signature hits first
    3. then a stable fallback order
    """
    hit_counts = anywhere_signature_hit_counts(data)
    remaining = [kind for kind in ALL_KINDS if kind not in primary_kinds]

    remaining.sort(
        key=lambda kind: (
            0 if hit_counts.get(kind, 0) > 0 else 1,
            -hit_counts.get(kind, 0),
            ALL_KINDS.index(kind),
        )
    )
    return remaining


def output_path_for(input_path: Path, input_root: Path, output_root: Path, declared_kind: str | None) -> Path:
    """
    Preserve original filename when the input has a recognized image extension.

    If the file had no recognized extension, use .png as the fallback output extension.
    """
    rel = input_path.relative_to(input_root)

    if declared_kind is not None:
        return output_root / rel

    fallback_ext = ".png"
    if rel.suffix:
        return output_root / rel
    return output_root / rel.parent / f"{rel.name}{fallback_ext}"


# -----------------------------------------------------------------------------
# Marker diagnostics
# -----------------------------------------------------------------------------

def marker_stats_for_kind(data: bytes, kind: str) -> dict:
    """
    Collect format-specific diagnostic marker counts.

    This is not just for curiosity; it directly informs what next strategies
    should be added if recovery still fails.
    """
    if kind == "jpeg":
        stats = {
            "soi_count": len(find_all(data, SOI)),
            "eoi_count": len(find_all(data, EOI)),
            "sos_count": len(find_all(data, SOS)),
            "dqt_count": len(find_all(data, DQT)),
            "dht_count": len(find_all(data, DHT)),
            "app0_count": len(find_all(data, APP0)),
            "app1_count": len(find_all(data, APP1)),
            "sof_count": sum(len(find_all(data, marker)) for marker in JPEG_SOF_MARKERS),
        }
        # JPEG restart markers can matter for partial recoverability
        rst_total = 0
        for i in range(8):
            rst_total += len(find_all(data, bytes([0xFF, 0xD0 + i])))
        stats["rst_count"] = rst_total
        return stats

    if kind == "png":
        return {
            "png_sig_count": len(find_all(data, PNG_SIG)),
            "ihdr_count": len(find_all(data, PNG_IHDR)),
            "idat_count": len(find_all(data, PNG_IDAT)),
            "iend_count": len(find_all(data, PNG_IEND)),
        }

    if kind == "gif":
        return {
            "gif87a_count": len(find_all(data, GIF87A)),
            "gif89a_count": len(find_all(data, GIF89A)),
            "gif_trailer_count": len(find_all(data, GIF_TRAILER)),
            "gif_image_separator_count": len(find_all(data, b"\x2c")),
        }

    if kind == "bmp":
        return {
            "bm_count": len(find_all(data, BMP_SIG)),
        }

    if kind == "tiff":
        return {
            "tiff_le_count": len(find_all(data, TIFF_LE)),
            "tiff_be_count": len(find_all(data, TIFF_BE)),
        }

    if kind == "webp":
        riff_positions = find_all(data, RIFF)
        webp_tag_positions = find_all(data, WEBP)
        return {
            "riff_count": len(riff_positions),
            "webp_tag_count": len(webp_tag_positions),
        }

    return {}


# -----------------------------------------------------------------------------
# Candidate builders
# -----------------------------------------------------------------------------

def add_candidate(bag: list[Candidate], seen: set[tuple], candidate: Candidate) -> None:
    key = (
        candidate.kind,
        candidate.strategy,
        candidate.start,
        candidate.end,
        candidate.prepend,
        candidate.append,
    )
    if key in seen:
        return
    seen.add(key)
    bag.append(candidate)


def materialize_candidate(data: bytes, candidate: Candidate) -> bytes:
    core = data[candidate.start:candidate.end] if candidate.end is not None else data[candidate.start:]
    return candidate.prepend + core + candidate.append



def _sample_sorted_positions(positions: list[int], limit: int) -> list[int]:
    if not positions:
        return []
    return sample_positions(sorted(set(positions)), limit)


def _select_nearby_end_positions(positions: list[int], max_items: int) -> list[int]:
    if not positions:
        return []
    return _sample_sorted_positions(positions, max_items)


def _nearest_previous_position(positions: list[int], pos: int) -> int | None:
    if not positions:
        return None
    idx = bisect.bisect_right(positions, pos) - 1
    if idx < 0:
        return None
    return positions[idx]


def collect_jpeg_candidates(data: bytes, limit: int) -> list[Candidate]:
    """
    Richer JPEG candidate generation.

    Why this is different from the previous version:
    - try more SOI -> EOI pairings, not just first/last
    - try truncated tails from SOI at multiple lengths
    - anchor on SOS and nearby structural markers
    - build more synthetic-SOI windows when internal JPEG structure exists but the real SOI/header is gone

    This targets the exact failure pattern shown by your logs:
    many files still contain JPEG structure but the current carve span is wrong.
    """
    bag: list[Candidate] = []
    seen: set[tuple] = set()

    add_candidate(bag, seen, Candidate("jpeg", "jpeg_raw_file", 0, None, priority=100))
    add_candidate(bag, seen, Candidate("jpeg", "jpeg_prepend_soi_whole", 0, None, prepend=SOI, priority=99))
    add_candidate(bag, seen, Candidate("jpeg", "jpeg_prepend_soi_whole_append_eoi", 0, None, prepend=SOI, append=EOI, priority=98))

    soi_positions = _sample_sorted_positions(find_all(data, SOI), max(1, min(limit, 12)))
    eoi_positions = find_all(data, EOI)
    sos_positions = _sample_sorted_positions(find_all(data, SOS), max(1, min(limit, 12)))

    dqt_positions = sorted(find_all(data, DQT))
    dht_positions = sorted(find_all(data, DHT))
    app0_positions = sorted(find_all(data, APP0))
    app1_positions = sorted(find_all(data, APP1))
    sof_positions: list[int] = []
    for marker in JPEG_SOF_MARKERS:
        sof_positions.extend(find_all(data, marker))
    sof_positions = sorted(sof_positions)

    internal_markers = app0_positions + app1_positions + dqt_positions + dht_positions + sos_positions + sof_positions
    internal_markers = _sample_sorted_positions(internal_markers, max(1, min(limit, 18)))

    # Pass A: better SOI-based carving
    tail_lengths = [65536, 262144, 1048576, 4194304]
    for soi in soi_positions:
        later_eois = [e for e in eoi_positions if e > soi]
        for eoi in _select_nearby_end_positions(later_eois, 6):
            add_candidate(bag, seen, Candidate("jpeg", "jpeg_soi_to_sampled_eoi", soi, eoi + 2, priority=97))
        if later_eois:
            add_candidate(bag, seen, Candidate("jpeg", "jpeg_soi_to_first_eoi", soi, later_eois[0] + 2, priority=96))
            add_candidate(bag, seen, Candidate("jpeg", "jpeg_soi_to_last_eoi", soi, later_eois[-1] + 2, priority=95))

        add_candidate(bag, seen, Candidate("jpeg", "jpeg_soi_to_end", soi, None, priority=94))
        add_candidate(bag, seen, Candidate("jpeg", "jpeg_soi_to_end_append_eoi", soi, None, append=EOI, priority=93))

        for length in tail_lengths:
            end = min(len(data), soi + length)
            if end - soi >= 128:
                add_candidate(bag, seen, Candidate("jpeg", f"jpeg_soi_tail_{length}", soi, end, priority=92))
                add_candidate(bag, seen, Candidate("jpeg", f"jpeg_soi_tail_{length}_append_eoi", soi, end, append=EOI, priority=91))

    # Pass B: SOS-anchored reconstruction windows
    marker_pool = sorted(set(soi_positions + app0_positions + app1_positions + dqt_positions + dht_positions + sof_positions))
    back_offsets = [0, 128, 512, 2048, 8192, 32768]
    for sos in sos_positions:
        starts: list[int] = [sos]
        prev_marker = _nearest_previous_position(marker_pool, sos)
        if prev_marker is not None:
            starts.append(prev_marker)

        # earliest structural marker in the recent neighborhood
        neighborhood = [p for p in marker_pool if 0 <= sos - p <= 131072]
        if neighborhood:
            starts.append(min(neighborhood))

        starts = sorted(set(starts))

        later_eois = [e for e in eoi_positions if e > sos]
        sampled_eois = _select_nearby_end_positions(later_eois, 4)

        for base_start in starts:
            for back in back_offsets:
                start = max(0, base_start - back)
                if later_eois:
                    for eoi in sampled_eois:
                        add_candidate(
                            bag,
                            seen,
                            Candidate("jpeg", f"jpeg_sos_cluster_back_{back}_to_eoi", start, eoi + 2, prepend=SOI, priority=90),
                        )
                add_candidate(
                    bag,
                    seen,
                    Candidate("jpeg", f"jpeg_sos_cluster_back_{back}_to_end", start, None, prepend=SOI, priority=89),
                )
                add_candidate(
                    bag,
                    seen,
                    Candidate("jpeg", f"jpeg_sos_cluster_back_{back}_to_end_append_eoi", start, None, prepend=SOI, append=EOI, priority=88),
                )

    # Pass C: generic internal-marker windows for missing SOI/header corruption
    for pos in internal_markers:
        for back in back_offsets:
            start = max(0, pos - back)
            add_candidate(
                bag,
                seen,
                Candidate("jpeg", f"jpeg_synthetic_soi_marker_back_{back}", start, None, prepend=SOI, priority=87),
            )
            add_candidate(
                bag,
                seen,
                Candidate("jpeg", f"jpeg_synthetic_soi_marker_back_{back}_append_eoi", start, None, prepend=SOI, append=EOI, priority=86),
            )

            later_eois = [e for e in eoi_positions if e > pos]
            for eoi in _select_nearby_end_positions(later_eois, 3):
                add_candidate(
                    bag,
                    seen,
                    Candidate("jpeg", f"jpeg_synthetic_soi_marker_back_{back}_to_eoi", start, eoi + 2, prepend=SOI, priority=85),
                )

    bag.sort(key=lambda c: (-c.priority, c.start, 10**18 if c.end is None else -c.end))
    return bag


def collect_png_candidates(data: bytes, limit: int) -> list[Candidate]:
    bag: list[Candidate] = []
    seen: set[tuple] = set()

    add_candidate(bag, seen, Candidate("png", "png_raw_file", 0, None, priority=100))

    sig_positions = sample_positions(find_all(data, PNG_SIG), limit)
    iend_positions = find_all(data, PNG_IEND)
    ihdr_positions = sample_positions(find_all(data, PNG_IHDR), limit)

    for pos in sig_positions:
        later_iends = [i for i in iend_positions if i > pos]
        if later_iends:
            add_candidate(bag, seen, Candidate("png", "png_sig_to_first_iend", pos, later_iends[0] + len(PNG_IEND), priority=99))
            add_candidate(bag, seen, Candidate("png", "png_sig_to_last_iend", pos, later_iends[-1] + len(PNG_IEND), priority=98))
        add_candidate(bag, seen, Candidate("png", "png_sig_to_end", pos, None, priority=97))

    # If PNG signature is broken but IHDR survived, try reconstructing signature.
    for pos in ihdr_positions:
        if pos >= 4:
            start = pos - 4
            later_iends = [i for i in iend_positions if i > start]
            if later_iends:
                add_candidate(bag, seen, Candidate("png", "png_prepend_sig_at_ihdr_first_iend", start, later_iends[0] + len(PNG_IEND), prepend=PNG_SIG, priority=95))
                add_candidate(bag, seen, Candidate("png", "png_prepend_sig_at_ihdr_last_iend", start, later_iends[-1] + len(PNG_IEND), prepend=PNG_SIG, priority=94))
            add_candidate(bag, seen, Candidate("png", "png_prepend_sig_at_ihdr_to_end", start, None, prepend=PNG_SIG, priority=93))

    add_candidate(bag, seen, Candidate("png", "png_prepend_sig_whole", 0, None, prepend=PNG_SIG, priority=92))

    bag.sort(key=lambda c: (-c.priority, c.start, 10**18 if c.end is None else -c.end))
    return bag


def collect_gif_candidates(data: bytes, limit: int) -> list[Candidate]:
    bag: list[Candidate] = []
    seen: set[tuple] = set()

    add_candidate(bag, seen, Candidate("gif", "gif_raw_file", 0, None, priority=100))

    header_positions = sorted(set(find_all(data, GIF87A) + find_all(data, GIF89A)))
    header_positions = sample_positions(header_positions, limit)

    trailer_positions = find_all(data, GIF_TRAILER)

    for pos in header_positions:
        later_trailers = [t for t in trailer_positions if t > pos]
        if later_trailers:
            add_candidate(bag, seen, Candidate("gif", "gif_header_to_first_trailer", pos, later_trailers[0] + 1, priority=99))
            add_candidate(bag, seen, Candidate("gif", "gif_header_to_last_trailer", pos, later_trailers[-1] + 1, priority=98))
        add_candidate(bag, seen, Candidate("gif", "gif_header_to_end", pos, None, priority=97))

    bag.sort(key=lambda c: (-c.priority, c.start, 10**18 if c.end is None else -c.end))
    return bag


def collect_bmp_candidates(data: bytes, limit: int) -> list[Candidate]:
    bag: list[Candidate] = []
    seen: set[tuple] = set()

    add_candidate(bag, seen, Candidate("bmp", "bmp_raw_file", 0, None, priority=100))

    bm_positions = sample_positions(find_all(data, BMP_SIG), limit)
    for pos in bm_positions:
        if pos + 6 <= len(data):
            declared_size = int.from_bytes(data[pos + 2:pos + 6], "little", signed=False)
            if 64 <= declared_size <= len(data) - pos:
                add_candidate(bag, seen, Candidate("bmp", "bmp_declared_size", pos, pos + declared_size, priority=99))
        add_candidate(bag, seen, Candidate("bmp", "bmp_to_end", pos, None, priority=98))

    bag.sort(key=lambda c: (-c.priority, c.start, 10**18 if c.end is None else -c.end))
    return bag


def collect_tiff_candidates(data: bytes, limit: int) -> list[Candidate]:
    bag: list[Candidate] = []
    seen: set[tuple] = set()

    add_candidate(bag, seen, Candidate("tiff", "tiff_raw_file", 0, None, priority=100))

    header_positions = sorted(set(find_all(data, TIFF_LE) + find_all(data, TIFF_BE)))
    header_positions = sample_positions(header_positions, limit)
    for pos in header_positions:
        add_candidate(bag, seen, Candidate("tiff", "tiff_header_to_end", pos, None, priority=99))

    bag.sort(key=lambda c: (-c.priority, c.start, 10**18 if c.end is None else -c.end))
    return bag


def collect_webp_candidates(data: bytes, limit: int) -> list[Candidate]:
    bag: list[Candidate] = []
    seen: set[tuple] = set()

    add_candidate(bag, seen, Candidate("webp", "webp_raw_file", 0, None, priority=100))

    riff_positions = sample_positions(find_all(data, RIFF), limit)
    for pos in riff_positions:
        if pos + 12 <= len(data) and data[pos + 8:pos + 12] == WEBP:
            declared_size = int.from_bytes(data[pos + 4:pos + 8], "little", signed=False) + 8
            if 64 <= declared_size <= len(data) - pos:
                add_candidate(bag, seen, Candidate("webp", "webp_declared_size", pos, pos + declared_size, priority=99))
            add_candidate(bag, seen, Candidate("webp", "webp_to_end", pos, None, priority=98))

    bag.sort(key=lambda c: (-c.priority, c.start, 10**18 if c.end is None else -c.end))
    return bag


def collect_candidates_for_kind(data: bytes, kind: str, limit: int) -> list[Candidate]:
    if kind == "jpeg":
        return collect_jpeg_candidates(data, limit)
    if kind == "png":
        return collect_png_candidates(data, limit)
    if kind == "gif":
        return collect_gif_candidates(data, limit)
    if kind == "bmp":
        return collect_bmp_candidates(data, limit)
    if kind == "tiff":
        return collect_tiff_candidates(data, limit)
    if kind == "webp":
        return collect_webp_candidates(data, limit)
    return []


# -----------------------------------------------------------------------------
# Decoder helpers
# -----------------------------------------------------------------------------

def normalize_for_save(img: Image.Image, output_kind: str) -> Image.Image:
    """
    Convert the image into a mode suitable for the target output format.

    This is deliberately conservative. The goal is "viewable recovered result",
    not perfect fidelity to the original encoding.
    """
    img = ImageOps.exif_transpose(img)

    # Animated formats: recover first frame only for now.
    if getattr(img, "is_animated", False):
        try:
            img.seek(0)
        except Exception:
            pass

    if output_kind == "jpeg":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return img

    if output_kind == "png":
        if img.mode in ("1", "L", "LA", "P", "RGB", "RGBA"):
            return img
        if img.mode == "CMYK":
            return img.convert("RGB")
        return img.convert("RGBA")

    if output_kind == "gif":
        if img.mode not in ("P", "L"):
            img = img.convert("P", palette=Image.ADAPTIVE)
        return img

    if output_kind == "bmp":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return img

    if output_kind == "tiff":
        if img.mode in ("1", "L", "LA", "P", "RGB", "RGBA", "CMYK"):
            return img
        return img.convert("RGB")

    if output_kind == "webp":
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGBA")
        return img

    return img.convert("RGB")


def probe_with_pillow(blob: bytes) -> DecodeMeta:
    try:
        with Image.open(io.BytesIO(blob)) as img:
            img.load()
            return DecodeMeta(
                ok=True,
                width=img.width,
                height=img.height,
                mode=img.mode,
                decoded_format=str(img.format or ""),
                decoder="pillow",
            )
    except Exception as e:
        return DecodeMeta(ok=False, decoder="pillow", error=compact_error(str(e)))


def save_with_pillow(blob: bytes, output_path: Path, output_kind: str) -> DecodeMeta:
    try:
        with Image.open(io.BytesIO(blob)) as img:
            img.load()
            img = normalize_for_save(img, output_kind)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            save_kwargs = {}
            if output_kind == "jpeg":
                save_kwargs = {"quality": 95, "optimize": False}
            elif output_kind == "png":
                save_kwargs = {"optimize": False, "compress_level": 1}
            elif output_kind == "webp":
                save_kwargs = {"quality": 95, "method": 4}

            img.save(output_path, format=KIND_TO_PIL_SAVE_FORMAT[output_kind], **save_kwargs)

            return DecodeMeta(
                ok=True,
                width=img.width,
                height=img.height,
                mode=img.mode,
                decoded_format=output_kind.upper(),
                decoder="pillow",
            )
    except Exception as e:
        return DecodeMeta(ok=False, decoder="pillow", error=compact_error(str(e)))


def ffmpeg_input_suffix(kind: str) -> str:
    return {
        "jpeg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "bmp": ".bmp",
        "tiff": ".tif",
        "webp": ".webp",
    }.get(kind, ".bin")


def probe_with_ffmpeg(blob: bytes, input_kind: str) -> DecodeMeta:
    if not FFMPEG_PATH:
        return DecodeMeta(ok=False, decoder="ffmpeg", error="ffmpeg_not_found")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"in{ffmpeg_input_suffix(input_kind)}"
        output_png = tmpdir_path / "probe.png"

        input_path.write_bytes(blob)

        cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-frames:v", "1",
            str(output_png),
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=12,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return DecodeMeta(ok=False, decoder="ffmpeg", error="ffmpeg_timeout")
        except Exception as e:
            return DecodeMeta(ok=False, decoder="ffmpeg", error=compact_error(str(e)))

        stderr_text = compact_error(proc.stderr.decode("utf-8", errors="replace"))

        if proc.returncode != 0 or not output_png.exists() or output_png.stat().st_size == 0:
            return DecodeMeta(ok=False, decoder="ffmpeg", error=stderr_text or "ffmpeg_failed")

        try:
            with Image.open(output_png) as img:
                img.load()
                return DecodeMeta(
                    ok=True,
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    decoded_format="PNG",
                    decoder="ffmpeg",
                )
        except Exception as e:
            return DecodeMeta(ok=False, decoder="ffmpeg", error=compact_error(str(e)))


def save_with_ffmpeg(blob: bytes, input_kind: str, output_path: Path, output_kind: str) -> DecodeMeta:
    """
    FFmpeg is used only as a decoder here.
    It writes a temporary PNG, then Pillow re-saves that into the intended final format.

    Why:
    - FFmpeg can sometimes decode candidates Pillow rejects.
    - We still want final output filenames / extensions to match the intended format.
    """
    if not FFMPEG_PATH:
        return DecodeMeta(ok=False, decoder="ffmpeg", error="ffmpeg_not_found")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"in{ffmpeg_input_suffix(input_kind)}"
        temp_png = tmpdir_path / "decoded.png"

        input_path.write_bytes(blob)

        cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-err_detect", "ignore_err",
            "-fflags", "+discardcorrupt",
            "-i", str(input_path),
            "-frames:v", "1",
            str(temp_png),
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=12,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return DecodeMeta(ok=False, decoder="ffmpeg", error="ffmpeg_timeout")
        except Exception as e:
            return DecodeMeta(ok=False, decoder="ffmpeg", error=compact_error(str(e)))

        stderr_text = compact_error(proc.stderr.decode("utf-8", errors="replace"))

        if proc.returncode != 0 or not temp_png.exists() or temp_png.stat().st_size == 0:
            return DecodeMeta(ok=False, decoder="ffmpeg", error=stderr_text or "ffmpeg_failed")

        try:
            with Image.open(temp_png) as img:
                img.load()
                img = normalize_for_save(img, output_kind)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                save_kwargs = {}
                if output_kind == "jpeg":
                    save_kwargs = {"quality": 95, "optimize": False}
                elif output_kind == "png":
                    save_kwargs = {"optimize": False, "compress_level": 1}
                elif output_kind == "webp":
                    save_kwargs = {"quality": 95, "method": 4}

                img.save(output_path, format=KIND_TO_PIL_SAVE_FORMAT[output_kind], **save_kwargs)

                return DecodeMeta(
                    ok=True,
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    decoded_format=output_kind.upper(),
                    decoder="ffmpeg",
                )
        except Exception as e:
            return DecodeMeta(ok=False, decoder="ffmpeg", error=compact_error(str(e)))


# -----------------------------------------------------------------------------
# Recovery / reasoning engine
# -----------------------------------------------------------------------------

def add_attempt_log(attempts: list[dict], item: dict, attempt_log_limit: int) -> None:
    if attempt_log_limit == 0 or len(attempts) < attempt_log_limit:
        attempts.append(item)


def per_file_next_ideas(kind: str, marker_stats: dict, attempts: list[dict], success: bool) -> list[str]:
    """
    Generate per-file reasoning hints.

    These are not guarantees. They are deliberate hypotheses about what next
    code changes could help for files with similar structure.
    """
    ideas: list[str] = []
    if success:
        return ideas

    if kind == "jpeg":
        if marker_stats.get("soi_count", 0) == 0 and (
            marker_stats.get("sos_count", 0) > 0 or
            marker_stats.get("dqt_count", 0) > 0 or
            marker_stats.get("dht_count", 0) > 0 or
            marker_stats.get("sof_count", 0) > 0
        ):
            ideas.append("JPEG seems to have internal structure without SOI. Add more synthetic-SOI candidate families from DQT/DHT/SOF/SOS windows.")
        if marker_stats.get("soi_count", 0) > 0 and marker_stats.get("eoi_count", 0) == 0:
            ideas.append("JPEG has SOI but no EOI. Increase append-EOI attempts and tail-window attempts.")
        if marker_stats.get("rst_count", 0) > 0:
            ideas.append("JPEG contains restart markers. Add restart-segment based carving / salvage attempts.")
        if marker_stats.get("soi_count", 0) == 0 and marker_stats.get("sos_count", 0) == 0:
            ideas.append("JPEG appears to be missing both header and scan markers. Recovery may require block-level brute-force or external carving tools.")

    elif kind == "png":
        if marker_stats.get("ihdr_count", 0) > 0 and marker_stats.get("png_sig_count", 0) == 0:
            ideas.append("PNG has IHDR but no signature. Add more synthetic-signature / chunk-window attempts.")
        if marker_stats.get("idat_count", 0) > 0 and marker_stats.get("iend_count", 0) == 0:
            ideas.append("PNG has data but no IEND. Add append-IEND and chunk-length sanity repair attempts.")
        if marker_stats.get("idat_count", 0) == 0:
            ideas.append("PNG has no visible IDAT marker. Stream may be too damaged for simple salvage.")

    elif kind == "gif":
        if marker_stats.get("gif_trailer_count", 0) == 0:
            ideas.append("GIF has header but no trailer. Add synthetic trailer / block terminator attempts.")
        ideas.append("If GIFs matter, add deeper block-level GIF parsing instead of first-frame only salvage.")

    elif kind == "bmp":
        ideas.append("For BMP, add header-field repair attempts (pixel offset / DIB size / image size).")

    elif kind == "tiff":
        ideas.append("For TIFF, add IFD/strip-offset repair and endian-consistency checks.")

    elif kind == "webp":
        ideas.append("For WEBP, add RIFF size repair and VP8/VP8L/VP8X subtype-aware recovery.")

    if not attempts:
        ideas.append("No attempts were logged. Increase candidate generation and logging depth.")

    return ideas


def best_recovery_for_data(
    data: bytes,
    selected_kinds: list[str],
    try_ffmpeg: bool,
    max_candidates_per_kind: int,
    max_ffmpeg_candidates: int,
    attempt_log_limit: int,
) -> tuple[Candidate | None, DecodeMeta, dict]:
    """
    Try all candidates for the selected intended kind(s).

    Returns:
    - best successful candidate, if any
    - best successful DecodeMeta, if any
    - detailed debug bundle explaining what happened
    """
    debug = {
        "selected_kinds": selected_kinds,
        "kind_debug": [],
        "attempts": [],
    }

    best_candidate: Candidate | None = None
    best_meta = DecodeMeta(ok=False, error="no_candidate_succeeded")

    total_ffmpeg_candidates_used = 0

    for kind in selected_kinds:
        marker_stats = marker_stats_for_kind(data, kind)
        candidates = collect_candidates_for_kind(data, kind, max_candidates_per_kind)

        kind_entry = {
            "kind": kind,
            "marker_stats": marker_stats,
            "candidate_count": len(candidates),
        }
        debug["kind_debug"].append(kind_entry)

        # Pillow pass on all candidates for this kind
        for candidate in candidates:
            blob = materialize_candidate(data, candidate)
            meta = probe_with_pillow(blob)

            add_attempt_log(
                debug["attempts"],
                {
                    "decoder": "pillow",
                    "kind": candidate.kind,
                    "strategy": candidate.strategy,
                    "start": candidate.start,
                    "end": candidate.end,
                    "prepend_len": len(candidate.prepend),
                    "append_len": len(candidate.append),
                    "ok": meta.ok,
                    "width": meta.width,
                    "height": meta.height,
                    "mode": meta.mode,
                    "decoded_format": meta.decoded_format,
                    "error": meta.error,
                },
                attempt_log_limit,
            )

            if meta.ok and ((not best_meta.ok) or meta.area > best_meta.area):
                best_candidate = candidate
                best_meta = meta

        # FFmpeg fallback on the top subset only
        if try_ffmpeg and best_candidate is None:
            for candidate in candidates[:max_ffmpeg_candidates]:
                blob = materialize_candidate(data, candidate)
                meta = probe_with_ffmpeg(blob, candidate.kind)

                total_ffmpeg_candidates_used += 1

                add_attempt_log(
                    debug["attempts"],
                    {
                        "decoder": "ffmpeg",
                        "kind": candidate.kind,
                        "strategy": candidate.strategy,
                        "start": candidate.start,
                        "end": candidate.end,
                        "prepend_len": len(candidate.prepend),
                        "append_len": len(candidate.append),
                        "ok": meta.ok,
                        "width": meta.width,
                        "height": meta.height,
                        "mode": meta.mode,
                        "decoded_format": meta.decoded_format,
                        "error": meta.error,
                    },
                    attempt_log_limit,
                )

                if meta.ok and ((not best_meta.ok) or meta.area > best_meta.area):
                    best_candidate = candidate
                    best_meta = meta

    debug["ffmpeg_candidates_used"] = total_ffmpeg_candidates_used
    return best_candidate, best_meta, debug



def recover_one(
    input_path: Path,
    input_root: Path,
    output_root: Path,
    overwrite: bool,
    try_ffmpeg: bool,
    max_candidates_per_kind: int,
    max_ffmpeg_candidates: int,
    attempt_log_limit: int,
) -> tuple[dict, dict]:
    data = read_bytes(input_path)

    declared_kind = declared_kind_from_extension(input_path)
    byte0_kind = header_kind_at_byte0(data)
    selected_kinds, selection_policy = selected_kinds_for_file(input_path, data)
    fallback_kinds = fallback_kinds_after_primary(selected_kinds, data, declared_kind)

    output_kind = declared_kind or (selected_kinds[0] if selected_kinds else "png")
    out_path = output_path_for(input_path, input_root, output_root, declared_kind)

    row = {
        "path": str(input_path),
        "size": str(len(data)),
        "declared_kind": declared_kind or "none",
        "byte0_kind": byte0_kind,
        "selection_policy": selection_policy,
        "selected_kinds": ",".join(selected_kinds),
        "success": "0",
        "decoder": "",
        "strategy": "",
        "width": "",
        "height": "",
        "mode": "",
        "output_path": str(out_path),
        "error": "",
    }

    detail = {
        "path": str(input_path),
        "size": len(data),
        "declared_kind": declared_kind,
        "byte0_kind": byte0_kind,
        "selection_policy": selection_policy,
        "selected_kinds": selected_kinds,
        "fallback_kinds": fallback_kinds,
        "anywhere_signature_hit_counts": anywhere_signature_hit_counts(data),
        "output_kind": output_kind,
        "output_path": str(out_path),
        "marker_stats_by_kind": {},
        "attempts": [],
        "next_ideas": [],
    }

    for kind in ALL_KINDS:
        detail["marker_stats_by_kind"][kind] = marker_stats_for_kind(data, kind)

    if out_path.exists() and not overwrite:
        row["error"] = "output_exists"
        detail["next_ideas"] = ["Use --overwrite if you want to replace existing recovered files."]
        return row, detail

    best_candidate, best_meta, debug = best_recovery_for_data(
        data=data,
        selected_kinds=selected_kinds,
        try_ffmpeg=try_ffmpeg,
        max_candidates_per_kind=max_candidates_per_kind,
        max_ffmpeg_candidates=max_ffmpeg_candidates,
        attempt_log_limit=attempt_log_limit,
    )

    for item in debug["attempts"]:
        item["pass"] = "primary"
    detail["attempts"].extend(debug["attempts"])
    detail["kind_debug"] = [{"pass": "primary", **item} for item in debug["kind_debug"]]
    detail["ffmpeg_candidates_used"] = debug["ffmpeg_candidates_used"]

    fallback_debug = None
    fallback_best_candidate = None
    fallback_best_meta = DecodeMeta(ok=False, error="no_candidate_succeeded")

    if (best_candidate is None or not best_meta.ok) and fallback_kinds:
        fallback_limit = max(8, min(24, max_candidates_per_kind // 3 if max_candidates_per_kind > 0 else 12))
        fallback_ffmpeg_limit = min(4, max_ffmpeg_candidates)

        fallback_best_candidate, fallback_best_meta, fallback_debug = best_recovery_for_data(
            data=data,
            selected_kinds=fallback_kinds,
            try_ffmpeg=False if not try_ffmpeg else try_ffmpeg,
            max_candidates_per_kind=fallback_limit,
            max_ffmpeg_candidates=fallback_ffmpeg_limit,
            attempt_log_limit=attempt_log_limit,
        )

        for item in fallback_debug["attempts"]:
            item["pass"] = "fallback_all_kinds"
        detail["attempts"].extend(fallback_debug["attempts"])
        detail["kind_debug"].extend([{"pass": "fallback_all_kinds", **item} for item in fallback_debug["kind_debug"]])
        detail["ffmpeg_candidates_used"] += fallback_debug["ffmpeg_candidates_used"]

        if fallback_best_candidate is not None and fallback_best_meta.ok:
            best_candidate = fallback_best_candidate
            best_meta = fallback_best_meta
            row["selection_policy"] = selection_policy + "_then_fallback_all_kinds"
            row["selected_kinds"] = ",".join(selected_kinds + fallback_kinds)

    if best_candidate is None or not best_meta.ok:
        row["error"] = best_meta.error or "no_candidate_succeeded"

        ideas: list[str] = []
        for kind in selected_kinds:
            ideas.extend(
                per_file_next_ideas(
                    kind=kind,
                    marker_stats=detail["marker_stats_by_kind"].get(kind, {}),
                    attempts=detail["attempts"],
                    success=False,
                )
            )

        if fallback_kinds:
            ideas.append("Primary intended kind failed, so the script also tried the remaining supported image kinds as a fallback.")
            kinds_with_hits = [kind for kind, count in detail["anywhere_signature_hit_counts"].items() if count > 0]
            if kinds_with_hits:
                ideas.append("Other format signatures were found somewhere in the blob: " + ", ".join(kinds_with_hits) + ".")

        detail["next_ideas"] = ideas
        return row, detail

    blob = materialize_candidate(data, best_candidate)

    save_meta = save_with_pillow(blob, out_path, output_kind)
    if not save_meta.ok and try_ffmpeg:
        save_meta = save_with_ffmpeg(blob, best_candidate.kind, out_path, output_kind)

    if not save_meta.ok:
        row["error"] = save_meta.error or "save_failed"
        detail["next_ideas"] = [
            "Decode succeeded at probe time but save failed.",
            "Inspect output mode conversion rules for this declared format.",
            "Consider temporarily saving recovered output as PNG for this format family.",
        ]
        return row, detail

    row["success"] = "1"
    row["decoder"] = save_meta.decoder
    row["strategy"] = best_candidate.strategy
    row["width"] = str(save_meta.width)
    row["height"] = str(save_meta.height)
    row["mode"] = save_meta.mode

    detail["best_candidate"] = {
        "kind": best_candidate.kind,
        "strategy": best_candidate.strategy,
        "start": best_candidate.start,
        "end": best_candidate.end,
        "prepend_len": len(best_candidate.prepend),
        "append_len": len(best_candidate.append),
    }
    detail["final_decoder"] = save_meta.decoder
    detail["final_width"] = save_meta.width
    detail["final_height"] = save_meta.height
    detail["final_mode"] = save_meta.mode
    detail["next_ideas"] = []

    return row, detail


# -----------------------------------------------------------------------------
# Report writers# -----------------------------------------------------------------------------
# Report writers
# -----------------------------------------------------------------------------

def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "size",
        "declared_kind",
        "byte0_kind",
        "selection_policy",
        "selected_kinds",
        "success",
        "decoder",
        "strategy",
        "width",
        "height",
        "mode",
        "output_path",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_detail_jsonl(details: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in details:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def count_by(rows: list[dict], key: str, failed_only: bool | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if failed_only is True and row["success"] == "1":
            continue
        if failed_only is False and row["success"] != "1":
            continue
        value = row.get(key, "") or "none"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def build_global_recommendations(rows: list[dict], details: list[dict]) -> list[str]:
    """
    Turn the aggregate evidence into concrete next coding ideas.
    """
    recommendations: list[str] = []

    total = len(rows)
    recovered = sum(1 for r in rows if r["success"] == "1")
    failed = total - recovered

    if failed > 0:
        error_counts = count_by(rows, "error", failed_only=True)
        if error_counts.get("no_candidate_succeeded", 0) > failed * 0.7:
            recommendations.append(
                "Most failures had no successful candidate. Candidate generation is the main bottleneck; add richer kind-specific carving before adding more save logic."
            )

    decoder_success = count_by(rows, "decoder", failed_only=False)
    if decoder_success.get("ffmpeg", 0) > decoder_success.get("pillow", 0):
        recommendations.append(
            "FFmpeg outperformed Pillow on successful recoveries. Consider increasing --max-ffmpeg-candidates or letting FFmpeg run earlier for the declared format."
        )

    # Aggregate marker-based hints by declared format
    jpeg_no_soi_but_internal = 0
    jpeg_soi_no_eoi = 0
    png_ihdr_no_sig = 0
    png_idat_no_iend = 0

    for detail, row in zip(details, rows):
        if row["success"] == "1":
            continue

        declared_kind = row["declared_kind"]
        marker_by_kind = detail.get("marker_stats_by_kind", {})

        if declared_kind == "jpeg":
            stats = marker_by_kind.get("jpeg", {})
            if stats.get("soi_count", 0) == 0 and (
                stats.get("sos_count", 0) > 0 or
                stats.get("dqt_count", 0) > 0 or
                stats.get("dht_count", 0) > 0 or
                stats.get("sof_count", 0) > 0
            ):
                jpeg_no_soi_but_internal += 1
            if stats.get("soi_count", 0) > 0 and stats.get("eoi_count", 0) == 0:
                jpeg_soi_no_eoi += 1

        if declared_kind == "png":
            stats = marker_by_kind.get("png", {})
            if stats.get("ihdr_count", 0) > 0 and stats.get("png_sig_count", 0) == 0:
                png_ihdr_no_sig += 1
            if stats.get("idat_count", 0) > 0 and stats.get("iend_count", 0) == 0:
                png_idat_no_iend += 1

    if jpeg_no_soi_but_internal > 0:
        recommendations.append(
            f"{jpeg_no_soi_but_internal} failed JPEGs had internal JPEG structure but no SOI. Add more synthetic-SOI strategies from DQT/DHT/SOF/SOS windows."
        )
    if jpeg_soi_no_eoi > 0:
        recommendations.append(
            f"{jpeg_soi_no_eoi} failed JPEGs had SOI but no EOI. Add stronger append-EOI and truncated-tail strategies."
        )
    if png_ihdr_no_sig > 0:
        recommendations.append(
            f"{png_ihdr_no_sig} failed PNGs had IHDR but no PNG signature. Add more synthetic-signature / chunk-window recovery."
        )
    if png_idat_no_iend > 0:
        recommendations.append(
            f"{png_idat_no_iend} failed PNGs had IDAT but no IEND. Add append-IEND and chunk-repair logic."
        )

    recommendations.append(
        "Inspect recover_detail.jsonl for failed files and sort by declared_kind, marker_stats_by_kind, and the earliest failing strategies. That file is the source of truth for what to add next."
    )

    return recommendations


def write_summary(rows: list[dict], details: list[dict], path: Path) -> None:
    summary = {
        "total": len(rows),
        "recovered": sum(1 for r in rows if r["success"] == "1"),
        "failed": sum(1 for r in rows if r["success"] != "1"),
        "by_declared_kind": count_by(rows, "declared_kind"),
        "by_byte0_kind": count_by(rows, "byte0_kind"),
        "by_selection_policy": count_by(rows, "selection_policy"),
        "by_strategy": count_by(rows, "strategy"),
        "by_decoder": count_by(rows, "decoder"),
        "top_errors": dict(list(count_by(rows, "error", failed_only=True).items())[:30]),
        "recommendations": build_global_recommendations(rows, details),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recover damaged images with extension-first format policy and detailed diagnostics."
    )
    parser.add_argument("input_folder", type=Path)
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--all-files", action="store_true", help="Scan all files, not only known image extensions.")
    parser.add_argument("--no-ffmpeg", action="store_true")
    parser.add_argument("--max-candidates-per-kind", type=int, default=80)
    parser.add_argument("--max-ffmpeg-candidates", type=int, default=8)
    parser.add_argument(
        "--attempt-log-limit",
        type=int,
        default=0,
        help="How many attempt records to keep per file in the detail JSONL. 0 = keep all.",
    )
    parser.add_argument("--report-csv", type=Path, default=Path("recover_report.csv"))
    parser.add_argument("--summary-json", type=Path, default=Path("recover_summary.json"))
    parser.add_argument("--detail-jsonl", type=Path, default=Path("recover_detail.jsonl"))
    args = parser.parse_args()

    if not args.input_folder.exists() or not args.input_folder.is_dir():
        print(f"Input folder is not a directory: {args.input_folder}")
        return 1

    files = list(iter_files(args.input_folder, args.recursive, args.all_files))
    if not files:
        print("No files found.")
        return 0

    try_ffmpeg = (not args.no_ffmpeg) and (FFMPEG_PATH is not None)

    print(f"Files: {len(files)}")
    print(f"FFmpeg available for fallback: {'yes' if try_ffmpeg else 'no'}")
    print()

    rows: list[dict] = []
    details: list[dict] = []

    for i, input_path in enumerate(files, start=1):
        try:
            row, detail = recover_one(
                input_path=input_path,
                input_root=args.input_folder,
                output_root=args.output_folder,
                overwrite=args.overwrite,
                try_ffmpeg=try_ffmpeg,
                max_candidates_per_kind=args.max_candidates_per_kind,
                max_ffmpeg_candidates=args.max_ffmpeg_candidates,
                attempt_log_limit=args.attempt_log_limit,
            )
        except Exception as e:
            row = {
                "path": str(input_path),
                "size": "",
                "declared_kind": declared_kind_from_extension(input_path) or "none",
                "byte0_kind": "",
                "selection_policy": "",
                "selected_kinds": "",
                "success": "0",
                "decoder": "",
                "strategy": "",
                "width": "",
                "height": "",
                "mode": "",
                "output_path": "",
                "error": f"script_exception:{compact_error(str(e))}",
            }
            detail = {
                "path": str(input_path),
                "exception": compact_error(str(e)),
                "next_ideas": [
                    "This is a script-side exception, not an image decode failure.",
                    "Inspect the stack trace and fix the recovery code path.",
                ],
            }

        rows.append(row)
        details.append(detail)

        if row["success"] == "1":
            print(
                f"[{i}/{len(files)}] OK   {row['path']} -> {row['output_path']} "
                f"| {row['width']}x{row['height']} | {row['strategy']} | {row['decoder']}"
            )
        else:
            print(f"[{i}/{len(files)}] FAIL {row['path']} | {row['error']}")

    write_csv(rows, args.report_csv)
    write_summary(rows, details, args.summary_json)
    write_detail_jsonl(details, args.detail_jsonl)

    recovered = sum(1 for r in rows if r["success"] == "1")
    failed = len(rows) - recovered

    print()
    print(f"Done. Recovered: {recovered}, Failed: {failed}, Total: {len(rows)}")
    print(f"CSV report:    {args.report_csv}")
    print(f"JSON summary:  {args.summary_json}")
    print(f"Detail JSONL:  {args.detail_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())