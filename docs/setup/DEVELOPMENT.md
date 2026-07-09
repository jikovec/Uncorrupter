# Developer Setup

## Requirements

- Python 3.11 or newer.
- `pip`.
- Optional: `ffmpeg` and `ffprobe` available on `PATH` for video recovery and FFmpeg fallback paths.

The package dependency declared in [pyproject.toml](../../pyproject.toml) is `Pillow>=10.0.0`.

## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

If you do not want a virtual environment, the editable install still works in any Python 3.11+ environment:

```powershell
python -m pip install -e .
```

## Optional FFmpeg

The code discovers FFmpeg with `shutil.which("ffmpeg")` and `shutil.which("ffprobe")` in [src/file_uncorrupter/decoders.py](../../src/file_uncorrupter/decoders.py).

When both tools are available:

- image recovery can use FFmpeg as a fallback after Pillow probing fails
- video/container probing uses ffprobe metadata plus an FFmpeg preview frame
- video recovery can produce remuxed video, preview frames, or a small frame set

When either tool is missing:

- FFmpeg-specific paths return a clear `ffmpeg_not_found` or `ffmpeg_or_ffprobe_not_found` style error
- FFmpeg-dependent tests are skipped by pytest

## Local Commands

Run all tests:

```powershell
python -m pytest
```

Run a quick scan:

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
```

Run recovery:

```powershell
file-uncorrupter recover .\input .\output --recursive --all-files --db .\runs.sqlite3 --save-raw-candidates
```

Export an existing report:

```powershell
file-uncorrupter report --db .\runs.sqlite3 --output-json .\report.json --output-csv .\attempts.csv
```

## Generated Files

Common generated files are ignored by [.gitignore](../../.gitignore):

- `__pycache__/`
- `.pytest_cache/`
- `.venv/`
- `*.pyc`
- `*.sqlite3`
- `*.db`
- `build/`
- `dist/`
- `*.egg-info/`

Recovery runs also create output folders, `_raw_candidates/` when requested, and `.uncorrupter-workspace/` under the selected output or database directory.

## Documentation And Agent Indexes

For docs-only orientation work, useful validation commands are:

```powershell
python -m json.tool .\docs\agent-index.json
git diff --check
```

The repo root can be opened as a local Obsidian vault for documentation. Keep `.obsidian/` ignored and do not add cloud, account, sync, or encryption setup during development.

Agent-facing navigation lives in:

- [../AGENT-INDEX.md](../AGENT-INDEX.md)
- [../SOURCE-MAP.md](../SOURCE-MAP.md)
- [../CONNECTIONS.md](../CONNECTIONS.md)
- [../agent-index.json](../agent-index.json)
