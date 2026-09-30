# File Uncorrupter

File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media. The current package is a modular recovery framework with SQLite evidence tracking, JPEG-focused repair strategies, baseline image/video carving, and optional FFmpeg-assisted video salvage.

## Status And Boundaries

- Package metadata version: `0.3.0`.
- Runtime `file_uncorrupter.__version__` currently reports `0.2.0`; reconciliation is tracked in GitHub issue #1.
- No GitHub release is currently published.
- The repository does not define a hosted service, HTTP API, telemetry upload, or deployment workflow.
- JPEG has the deepest recovery strategy coverage. Non-JPEG and video/container support is baseline recovery and depends on available local decoders.

## Documentation

Start with:

- [Documentation index](docs/INDEX.md)
- [Project overview](docs/PROJECT-OVERVIEW.md)
- [Developer setup](docs/setup/DEVELOPMENT.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [CLI reference](docs/api/CLI.md)
- [Testing and verification](docs/testing/VERIFICATION.md)
- [Security model](docs/security/SECURITY.md)
- [Agent orientation](docs/AGENT-INDEX.md)

Repository policies:

- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Support](SUPPORT.md)
- [Apache License 2.0](LICENSE)

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
- optional `ffmpeg` and `ffprobe` on `PATH` for FFmpeg-assisted recovery

Install locally:

```text
python -m pip install -e .
```

Run tests when `pytest` is installed in the active environment:

```text
python -m pytest
```

## Common Commands

Scan and classify files without recovery:

```text
file-uncorrupter scan input --recursive --all-files --db runs.sqlite3
file-uncorrupter classify input --recursive --all-files --db runs.sqlite3
```

Recover files:

```text
file-uncorrupter recover input output --recursive --all-files --db runs.sqlite3 --save-raw-candidates
```

Benchmark and export reports:

```text
file-uncorrupter benchmark input output --recursive --all-files --db runs.sqlite3 --output-json benchmark.json --output-csv attempts.csv
file-uncorrupter report --db runs.sqlite3 --run-id 1 --output-json report.json --output-csv attempts.csv
```

## Output And Evidence Notes

- Keep source evidence separate from output, database, report, raw-candidate, and workspace paths. Current code does not enforce every unsafe path-overlap case; see the security documentation and GitHub issue #8.
- Still-image outputs are normalized to the declared or detected image family where Pillow or FFmpeg can produce one.
- Video/container outputs are normalized to local artifacts, usually remuxed video plus preview/frame artifacts when FFmpeg can decode them.
- Raw winning candidates are stored under `<output>/_raw_candidates/...` when `--save-raw-candidates` is used.
- Workspace state defaults to `<output>/.uncorrupter-workspace/` for `recover` and `benchmark`, and to the database directory for `scan` and `classify`, unless `--workspace-root` is provided.
- SQLite databases and generated reports can contain local paths and media metadata; they are not anonymized.

## Historical Material

`VERSIONS/`, `src/file_uncorrupter/legacy/`, and `docs/reports/archive/` contain historical evidence. They are intentionally not current implementation authority.
