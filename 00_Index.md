# Uncorrupter

This repo root is configured as an Obsidian vault for project documentation and working context.

## Entry Points
- [docs/INDEX.md](docs/INDEX.md)
- [LICENSE](LICENSE)
- [README.md](README.md)

## Project Overview
- [docs/PROJECT-OVERVIEW.md](docs/PROJECT-OVERVIEW.md)
- [README.md](README.md)

## Architecture
- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

## Security And Compliance
- [docs/security/SECURITY.md](docs/security/SECURITY.md)

## Commands Setup And Operations
- [docs/setup/DEVELOPMENT.md](docs/setup/DEVELOPMENT.md)

## Testing And Verification
- [docs/testing/VERIFICATION.md](docs/testing/VERIFICATION.md)

## Releases And Changelogs
- [docs/releases/CHANGELOG.md](docs/releases/CHANGELOG.md)

## Reports And Handoffs
- [reports/2026-07-07-memory-workflow-validation.md](reports/2026-07-07-memory-workflow-validation.md)
- [reports/](reports/)
- [handoffs/](handoffs/)
- [docs/reports/archive/001-deep-research-report.md](docs/reports/archive/001-deep-research-report.md)
- [docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md](docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md)
- [docs/reports/INDEX.md](docs/reports/INDEX.md)

## Other Existing Notes
- [docs/api/CLI.md](docs/api/CLI.md)

## Working Notes
- [[docs/PROJECT-OVERVIEW|Project overview]]
- [[docs/architecture/ARCHITECTURE|Architecture]]
- [[docs/commands|Commands]]
- [[docs/current-state|Current state]]
- [[docs/decisions|Decisions]]
- [[docs/security-model|Security model]]
- [[docs/testing|Testing]]

## Maintenance
- Keep this index additive. Link existing docs instead of moving, renaming, or duplicating them.
- Store handoff notes in handoffs/ and generated review summaries in reports/ when they are useful to keep in the repo.


<!-- codex-memory-scaffold:project-map -->
## Project Map

### Purpose
- File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media. The current package is a modular recovery framework with SQLite evidence tracking, JPEG-focused repair strategies, baseline image/video carving, and optional FFmpeg-assisted video salvage.

### Apparent Stack
- Python (pyproject.toml, requirements.txt, or root Python files present)

### Key Source And Project Folders
- CHANGELOG
- docs
- DOCUMENTATION
- handoffs
- reports
- results
- src
- tests
- VERSIONS

### Memory Notes
- [[docs/current-state|Current state]]
- [[docs/decisions|Decisions]]
- [[docs/commands|Commands]]
- [[docs/testing|Testing]]
- [[docs/security-model|Security model]]
- handoffs/ for future handoff notes.
- reports/ for future review and validation reports.

### Existing Docs Linked During Setup
- [AGENTS.md](AGENTS.md)
- [LICENSE](LICENSE)
- [README.md](README.md)
- [docs/api/CLI.md](docs/api/CLI.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- [docs/commands.md](docs/commands.md)
- [docs/current-state.md](docs/current-state.md)
- [docs/decisions.md](docs/decisions.md)
- [docs/INDEX.md](docs/INDEX.md)
- [docs/PROJECT-OVERVIEW.md](docs/PROJECT-OVERVIEW.md)
- [docs/releases/CHANGELOG.md](docs/releases/CHANGELOG.md)
- [docs/reports/archive/001-deep-research-report.md](docs/reports/archive/001-deep-research-report.md)
- [docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md](docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md)
- [docs/reports/INDEX.md](docs/reports/INDEX.md)
- [docs/security-model.md](docs/security-model.md)
- [docs/security/SECURITY.md](docs/security/SECURITY.md)
- [docs/setup/DEVELOPMENT.md](docs/setup/DEVELOPMENT.md)
- [docs/testing.md](docs/testing.md)
- [docs/testing/VERIFICATION.md](docs/testing/VERIFICATION.md)

### Reports And Handoffs
- [reports/2026-07-07-memory-workflow-validation.md](reports/2026-07-07-memory-workflow-validation.md)
- [reports/](reports/)
- [handoffs/](handoffs/)
- [docs/reports/archive/001-deep-research-report.md](docs/reports/archive/001-deep-research-report.md)
- [docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md](docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md)
- [docs/reports/INDEX.md](docs/reports/INDEX.md)

### README, Changelogs, And Release Notes
- [README.md](README.md)
- [docs/releases/CHANGELOG.md](docs/releases/CHANGELOG.md)

### Testing Commands
- python -m pytest - explicit README command, source: README.md; detail: README documented command
- python -m pytest - inferred test command, source: tests/ + Python config; detail: tests directory with Python config present
<!-- /codex-memory-scaffold:project-map -->
