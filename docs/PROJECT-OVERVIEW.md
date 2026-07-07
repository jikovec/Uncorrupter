# Project Overview

File Uncorrupter is a local-first corrupted-media recovery framework. It scans input files, records signatures and classification evidence, generates recovery candidates, probes candidates with decoders, scores successful candidates, writes recovered artifacts, and stores run evidence in SQLite.

## Current Package Shape

- Package name: `file-uncorrupter`
- Console script: `file-uncorrupter`
- Package metadata version: `0.3.0` in [pyproject.toml](../pyproject.toml)
- Python requirement: `>=3.11`
- Runtime dependency declared by the package: `Pillow>=10.0.0`
- Optional local tools: `ffmpeg` and `ffprobe` for video probing/recovery and FFmpeg image fallback

Known version-surface inconsistency:

- [src/file_uncorrupter/__init__.py](../src/file_uncorrupter/__init__.py) currently exposes `__version__ = "0.2.0"` while [pyproject.toml](../pyproject.toml) declares `0.3.0`.
- This documentation records the inconsistency without changing runtime behavior.

## Main Capabilities

- `scan`: collect file, signature, and classification evidence.
- `classify`: scan and classify input files.
- `recover`: generate candidates, decode/probe them, write recovered outputs, and persist evidence.
- `benchmark`: run recovery and export optional JSON/CSV reports.
- `report`: export reports from an existing run database.

## Supported Families In Code

The configured family list comes from [src/file_uncorrupter/constants.py](../src/file_uncorrupter/constants.py) and [src/file_uncorrupter/engines/media_v2.py](../src/file_uncorrupter/engines/media_v2.py).

Image families:

- `jpeg`
- `png`
- `gif`
- `bmp`
- `tiff`
- `webp`
- `heif`
- `avif`
- `jp2`
- `raw`

Video/container families:

- `mp4`
- `mov`
- `avi`
- `mkv`
- `webm`
- `mpegts`
- `mpegps`
- `flv`
- `asf`
- `wmv`

Important implementation boundary:

- JPEG has the deepest current repair strategy coverage.
- Generic non-JPEG image families use full-file and signature-offset candidates.
- Video/container recovery depends on local `ffmpeg` and `ffprobe`.
- Some listed families are detectable and candidate-generatable even when the local decoder stack cannot fully recover them.

## Important Source Paths

- [src/file_uncorrupter/cli.py](../src/file_uncorrupter/cli.py) - command definitions and command dispatch.
- [src/file_uncorrupter/pipeline.py](../src/file_uncorrupter/pipeline.py) - scan, classify, recover, persist orchestration.
- [src/file_uncorrupter/intake.py](../src/file_uncorrupter/intake.py) - file iteration, byte reading, hashes, record construction.
- [src/file_uncorrupter/signature_index.py](../src/file_uncorrupter/signature_index.py) - byte-0 and anywhere signature detection.
- [src/file_uncorrupter/classification.py](../src/file_uncorrupter/classification.py) - family and label assignment.
- [src/file_uncorrupter/engines/](../src/file_uncorrupter/engines/) - candidate generation engines.
- [src/file_uncorrupter/decoders.py](../src/file_uncorrupter/decoders.py) - Pillow and FFmpeg adapters.
- [src/file_uncorrupter/db.py](../src/file_uncorrupter/db.py) - SQLite schema and persistence.
- [src/file_uncorrupter/reporting.py](../src/file_uncorrupter/reporting.py) - JSON and CSV report writers.
- [src/file_uncorrupter/workspace.py](../src/file_uncorrupter/workspace.py) - workspace layout and config snapshots.
- [tests/](../tests/) - current regression tests.

## Historical Material

The historical research blueprint is preserved at [docs/reports/archive/001-deep-research-report.md](reports/archive/001-deep-research-report.md). It is useful background, but it includes future-looking recommendations and references to uploaded artifacts. Prefer current source and tests for implementation facts.
