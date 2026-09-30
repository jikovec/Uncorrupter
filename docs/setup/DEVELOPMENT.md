# Developer Setup

## Requirements

- Python 3.11 or newer.
- `pip`.
- Optional: `ffmpeg` and `ffprobe` on `PATH` for FFmpeg-assisted image/video paths.

The package declares `Pillow>=10.0.0` as its runtime dependency. The repository does not currently declare an operating-system support matrix.

## Install

From the repository root:

```text
python -m venv .venv
python -m pip install -U pip
python -m pip install -e .
```

Activate the virtual environment using the normal command for your shell, for example:

```text
# POSIX shells
. .venv/bin/activate

# PowerShell
.\.venv\Scripts\Activate.ps1
```

An editable install without a virtual environment is also possible in an appropriate Python 3.11+ environment:

```text
python -m pip install -e .
```

## Optional FFmpeg

The current decoder module discovers `ffmpeg` and `ffprobe` with `shutil.which()`.

When available, FFmpeg/ffprobe can be used for image fallback, video/container probing, remuxing, preview extraction, and frame extraction. FFmpeg-dependent tests skip when the required executables are unavailable.

Treat untrusted media parsing as a security boundary; see [../security/SECURITY.md](../security/SECURITY.md).

## Common Development Commands

Run the test suite when `pytest` is installed:

```text
python -m pytest
```

Run a scan:

```text
file-uncorrupter scan input --recursive --all-files --db runs.sqlite3
```

Run recovery:

```text
file-uncorrupter recover input output --recursive --all-files --db runs.sqlite3 --save-raw-candidates
```

Export an existing report:

```text
file-uncorrupter report --db runs.sqlite3 --output-json report.json --output-csv attempts.csv
```

See [../api/CLI.md](../api/CLI.md) for the full current CLI surface.

## Generated And Local-Only Files

[.gitignore](../../.gitignore) excludes common Python/build/cache output, local SQLite databases, `.uncorrupter-workspace/`, `_raw_candidates/`, and local Obsidian settings.

Historical ZIP archives under `VERSIONS/` are intentionally tracked evidence and are not covered by a global archive ignore rule.

## Git And Work Management

Before editing:

```text
git status --short --branch
```

Preserve unrelated dirty/untracked work. For material work, use the current GitHub issue ledger and the normal flow:

`Issue -> branch -> implementation -> verification -> pull request`

Do not merge, release, publish, deploy, tag, or change repository settings unless the current task explicitly authorizes it.

## Documentation Validation

When documentation or agent indexes change:

```text
python -m json.tool docs/agent-index.json
git diff --check
```

There is no dedicated Markdown formatter/link-checker configured in the repository. Validate changed relative links against the tracked tree and record any unavailable checks rather than claiming they passed.
