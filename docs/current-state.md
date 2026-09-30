<!-- codex-memory-scaffold:current-state -->
# Current State

Last reviewed against GitHub `main`: 2026-09-30.

## Project Purpose

File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media. The current package uses SQLite evidence tracking, JPEG-focused repair strategies, baseline image/video recovery, and optional FFmpeg/ffprobe assistance.

## Tracked Top-Level Repository Areas

- `docs/`
- `handoffs/`
- `reports/`
- `src/`
- `tests/`
- `VERSIONS/`

Root files include `README.md`, `AGENTS.md`, `LICENSE`, `pyproject.toml`, `.gitignore`, repository policy files, and formatting metadata.

Historical documentation previously referred to root `CHANGELOG/`, `DOCUMENTATION/`, and `results/` directories. They are not tracked in the current tree.

## Current Technical Surface

- Package: `file-uncorrupter`
- Python requirement: `>=3.11`
- Runtime dependency: `Pillow>=10.0.0`
- Optional local tools: `ffmpeg`, `ffprobe`
- Console entry point: `file-uncorrupter = "file_uncorrupter.cli:main"`
- Commands: `scan`, `classify`, `recover`, `benchmark`, `report`
- Persistence: SQLite plus local workspace/config snapshots
- Network/service layer: none defined in current source
- Deployment workflow: none defined in the repository

## Canonical Documentation

- [Documentation index](INDEX.md)
- [Project overview](PROJECT-OVERVIEW.md)
- [Architecture](architecture/ARCHITECTURE.md)
- [Developer setup](setup/DEVELOPMENT.md)
- [CLI reference](api/CLI.md)
- [Testing and verification](testing/VERIFICATION.md)
- [Security and local data handling](security/SECURITY.md)
- [Source map](SOURCE-MAP.md)
- [Connection map](CONNECTIONS.md)
- [Agent orientation](AGENT-INDEX.md)
- [Machine-readable agent index](agent-index.json)
- [Decision log](decisions.md)

Repository policy/discovery files:

- [Contributing](../CONTRIBUTING.md)
- [Security reporting](../SECURITY.md)
- [Support](../SUPPORT.md)
- [License](../LICENSE)

## Work Management

Material current/future work is tracked in GitHub Issues. Repository work should use `Issue -> branch -> verification -> pull request` unless the active task explicitly establishes a different authorized workflow.

Current implementation gaps should be read from the live issue ledger rather than copied into this file.

## Historical Evidence

- `VERSIONS/` preserves historical release artifacts, including ZIP archives.
- `src/file_uncorrupter/legacy/` preserves legacy source evidence.
- `docs/reports/archive/` preserves historical research.
- Historical reports remain historically accurate even when superseded by current source or docs.

## Known Current Risks

- Package metadata declares version `0.3.0` while `src/file_uncorrupter/__init__.py` reports `0.2.0`; see GitHub issue #1.
- Pytest is configured but is not declared as a project dependency.
- FFmpeg/ffprobe-dependent behavior and tests depend on local tool availability.
- The security model is local-first but current code should not be assumed to enforce every source/output path-separation or resource-boundary case; consult the live issue ledger and security documentation.

## Local Worktree Boundary

GitHub `main` is authoritative for current shared repository state. A local worktree may contain unrelated dirty or untracked changes; always inspect `git status --short --branch` before editing and preserve unrelated work.
