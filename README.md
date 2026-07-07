# File Uncorrupter

File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media. The current package is a modular recovery framework with SQLite evidence tracking, JPEG-focused repair strategies, baseline image/video carving, and optional FFmpeg-assisted video salvage.

Start with the documentation index:

- [Documentation index](docs/INDEX.md)
- [Developer setup](docs/setup/DEVELOPMENT.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [CLI reference](docs/api/CLI.md)
- [Testing and verification](docs/testing/VERIFICATION.md)
- [Reports and archive](docs/reports/INDEX.md)

## Current Scope

Implemented CLI commands:

- `scan`
- `classify`
- `recover`
- `benchmark`
- `report`

Implemented recovery surface:

- media intake for known image and video extensions, or all files with `--all-files`
- byte-0 and anywhere-in-blob signature detection
- classification labels for JPEG structural failures and baseline container candidates
- `jpeg-v1` deep JPEG candidate generation
- `baseline-v2` media-generic candidate generation across configured image/video families
- Pillow probing/saving for supported still-image formats
- optional FFmpeg/ffprobe probing, remuxing, preview extraction, and frame extraction
- SQLite run database for files, signatures, candidates, attempts, outputs, and frames
- report export to JSON summary and attempts CSV
- workspace config snapshots under `.uncorrupter-workspace`

## Quick Start

Requirements:

- Python 3.11 or newer
- Pillow, installed from `pyproject.toml`
- Optional: `ffmpeg` and `ffprobe` on `PATH` for video salvage and FFmpeg image fallback

Install locally:

```powershell
python -m pip install -e .
```

Run tests:

```powershell
python -m pytest
```

## Common Commands

Scan and classify files without recovery:

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
file-uncorrupter classify .\input --recursive --all-files --db .\runs.sqlite3
```

Recover files:

```powershell
file-uncorrupter recover .\input .\output --recursive --all-files --db .\runs.sqlite3 --save-raw-candidates
```

Benchmark and export reports:

```powershell
file-uncorrupter benchmark .\input .\output --recursive --all-files --db .\runs.sqlite3 --output-json .\benchmark.json --output-csv .\attempts.csv
file-uncorrupter report --db .\runs.sqlite3 --run-id 1 --output-json .\report.json --output-csv .\attempts.csv
```

## Output Notes

- Still-image outputs are normalized to the declared or detected image family where Pillow or FFmpeg can produce one.
- Video/container outputs are normalized to robust local artifacts, usually MKV remuxes plus preview frames when FFmpeg can decode them.
- Raw winning candidates are stored under `<output>/_raw_candidates/...` when `--save-raw-candidates` is used.
- Workspace state defaults to `<output>/.uncorrupter-workspace/` for `recover` and `benchmark`, and to the database directory for `scan` and `classify`, unless `--workspace-root` is provided.
- The project metadata currently declares version `0.3.0`; see [changelog and release notes](docs/releases/CHANGELOG.md) for the current version-surface note.
