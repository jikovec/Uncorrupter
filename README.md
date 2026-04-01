# File Uncorrupter

File Uncorrupter is a recovery-oriented batch framework for corrupted image files.

This initial repository version restructures the project away from a single script into a modular CLI application with:

- intake and manifesting
- JPEG-first triage and classification
- pluggable recovery engines
- decoder adapters
- SQLite-backed experiment tracking
- structured reporting
- preserved legacy prototype code for reference

## Current scope

The current implementation is intentionally JPEG-first because the existing project evidence shows that nearly all observed files are declared JPEG and that the dominant failure patterns are JPEG structural failures rather than generic image-decoder failures.

Implemented now:

- `scan` command
- `classify` command
- `recover` command
- `report` command
- SQLite run database
- `jpeg-v1` recovery engine
- Pillow decoder adapter
- optional FFmpeg decoder adapter if available
- raw winning-candidate persistence
- legacy prototype snapshot under `src/file_uncorrupter/legacy/`

Planned next:

- stronger JPEG segment parser
- deeper restart-marker resynchronization
- native repair core
- per-strategy benchmark dashboards
- expansion beyond JPEG-first recovery

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -e .
```

## Commands

### Scan

```bash
file-uncorrupter scan /path/to/input --recursive --db runs.sqlite3
```

### Classify

```bash
file-uncorrupter classify /path/to/input --recursive --db runs.sqlite3
```

### Recover

```bash
file-uncorrupter recover /path/to/input /path/to/output --recursive --db runs.sqlite3 --save-raw-candidates
```

### Report

```bash
file-uncorrupter report --db runs.sqlite3 --run-id 1 --output-json report.json --output-csv attempts.csv
```

## Output layout

Recovery output is written into the chosen output directory.

When `--save-raw-candidates` is used, the winning candidate bytes are also stored under:

- `<output>/_raw_candidates/<relative-file-path>.candidate`

This keeps structural artifacts separate from normalized exports.

## Notes

- FFmpeg is optional. If present on PATH, it is used as a secondary decoder.
- The current engine does not assume the extension is absolute truth. Extension, header, and marker evidence are all considered.
- The legacy script is preserved for comparison, but the new codepath is the main path going forward.
