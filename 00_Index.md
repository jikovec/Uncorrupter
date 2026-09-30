# Uncorrupter

This repository root can be opened as a local Obsidian vault for project documentation and working context.

## Entry Points

- [README.md](README.md)
- [Documentation index](docs/INDEX.md)
- [Agent orientation](docs/AGENT-INDEX.md)
- [Project overview](docs/PROJECT-OVERVIEW.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Developer setup](docs/setup/DEVELOPMENT.md)
- [Testing](docs/testing/VERIFICATION.md)
- [Security](docs/security/SECURITY.md)

## Repository Policies

- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Support](SUPPORT.md)
- [License](LICENSE)

## Maps And Current State

- [Current state](docs/current-state.md)
- [Source map](docs/SOURCE-MAP.md)
- [Connection map](docs/CONNECTIONS.md)
- [Decision log](docs/decisions.md)
- [Machine-readable agent index](docs/agent-index.json)
- [Obsidian guide](docs/OBSIDIAN.md)

## Reports, Handoffs, And History

- [Root reports index](reports/INDEX.md)
- [Handoffs index](handoffs/INDEX.md)
- [Curated documentation reports](docs/reports/INDEX.md)
- [Historical research archive](docs/reports/archive/001-deep-research-report.md)
- [Historical release artifacts](VERSIONS/)

## Maintenance

- Keep this index concise and point to canonical documents rather than duplicating them.
- Current source, tests, package configuration, and live repository state outrank historical reports and archives.
- Keep `.obsidian/` local-only and plaintext; do not commit local workspace settings.
- After meaningful repository changes, update the affected current-state/map/index documents.

<!-- codex-memory-scaffold:project-map -->
## Project Map

### Purpose

File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media with SQLite evidence tracking, JPEG-focused recovery, baseline image/video recovery, and optional FFmpeg/ffprobe assistance.

### Tracked Top-Level Areas

- `docs/` - current documentation and historical documentation reports
- `handoffs/` - future-agent handoff notes
- `reports/` - durable validation and implementation evidence
- `src/` - current package source plus explicitly marked legacy evidence
- `tests/` - current pytest regression suite
- `VERSIONS/` - historical release evidence, not current source

### Core Commands

- `python -m pip install -e .`
- `python -m pytest`
- `file-uncorrupter scan`
- `file-uncorrupter classify`
- `file-uncorrupter recover`
- `file-uncorrupter benchmark`
- `file-uncorrupter report`

### Historical Path Note

Earlier documentation scaffolding referred to root `CHANGELOG/`, `DOCUMENTATION/`, and `results/` directories. They are not tracked in the current repository. Historical material formerly under `DOCUMENTATION/` is preserved under `docs/reports/archive/`.
<!-- /codex-memory-scaffold:project-map -->
