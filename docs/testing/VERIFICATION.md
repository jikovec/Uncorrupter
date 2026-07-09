# Testing And Verification

The current repository uses pytest. Test configuration lives in [pyproject.toml](../../pyproject.toml):

- `pythonpath = ["src"]`
- `testpaths = ["tests"]`

## Run The Test Suite

From the repository root:

```powershell
python -m pytest
```

FFmpeg-dependent video tests are skipped automatically when FFmpeg is not available.

## Current Test Coverage

Classification tests in [tests/test_classification.py](../../tests/test_classification.py):

- missing EOI JPEG classification
- missing SOI with internal JPEG structure classification

Signature tests in [tests/test_signature_index.py](../../tests/test_signature_index.py):

- anywhere signature detection for prefixed MP4 data

Database tests in [tests/test_db.py](../../tests/test_db.py):

- run summary counts
- duplicate candidate persistence
- successful image output summary counts

Recovery tests in [tests/test_recovery.py](../../tests/test_recovery.py):

- missing EOI JPEG recovery
- missing SOI JPEG recovery
- missing DHT JPEG recovery
- scattered-segment JPEG header rebuild
- synthetic SOS rebuilds
- prefixed MP4 recovery through signature offset when FFmpeg is available
- candidate generation assertions for missing SOI and missing SOS cases
- standard color table generation

## Basic Documentation Checks

There is no dedicated Markdown formatter or link checker configured in the repo at this time. For documentation-only changes, use:

```powershell
python -m json.tool .\docs\agent-index.json
git diff --check
```

Run `python -m pytest` when source, tests, package metadata, or behavior-facing docs change enough to require runtime confidence. Pytest must be installed in the active environment first.

Use a basic local Markdown link check when files are moved or new docs links are added.

## Manual Smoke Test

For a small local sample corpus:

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
file-uncorrupter recover .\input .\output --recursive --all-files --db .\runs.sqlite3 --save-raw-candidates
file-uncorrupter report --db .\runs.sqlite3 --output-json .\report.json --output-csv .\attempts.csv
```

Check:

- JSON summaries are printed
- `runs.sqlite3` is created
- `.uncorrupter-workspace/configs/` contains a run config snapshot
- recovered artifacts are under the chosen output directory
- `_raw_candidates/` exists only when `--save-raw-candidates` is used

## Agent Index Checks

When updating [../agent-index.json](../agent-index.json), validate it with:

```powershell
python -m json.tool .\docs\agent-index.json
```

When updating Obsidian or agent orientation docs, also check [../AGENT-INDEX.md](../AGENT-INDEX.md), [../OBSIDIAN.md](../OBSIDIAN.md), [../SOURCE-MAP.md](../SOURCE-MAP.md), and [../CONNECTIONS.md](../CONNECTIONS.md) for stale links.
