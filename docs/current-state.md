<!-- codex-memory-scaffold:current-state -->
# Current State

## Project Purpose
- File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media. The current package is a modular recovery framework with SQLite evidence tracking, JPEG-focused repair strategies, baseline image/video carving, and optional FFmpeg-assisted video salvage.

## Apparent Stack
- Python (pyproject.toml, requirements.txt, or root Python files present)

## Key Folders
- CHANGELOG
- docs
- DOCUMENTATION
- handoffs
- reports
- results
- src
- tests
- VERSIONS

## Manifest And Config Files
- pyproject.toml
- .gitignore

## Important Docs And Reports
- [AGENTS.md](../AGENTS.md)
- [LICENSE](../LICENSE)
- [README.md](../README.md)
- [00_Index.md](../00_Index.md)
- [docs/api/CLI.md](api/CLI.md)
- [docs/architecture.md](architecture.md)
- [docs/architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md)
- [docs/commands.md](commands.md)
- [docs/current-state.md](current-state.md)
- [docs/decisions.md](decisions.md)
- [docs/INDEX.md](INDEX.md)
- [docs/PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md)
- [docs/releases/CHANGELOG.md](releases/CHANGELOG.md)
- [docs/reports/archive/001-deep-research-report.md](reports/archive/001-deep-research-report.md)
- [docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md](reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md)
- [docs/reports/INDEX.md](reports/INDEX.md)
- [docs/security-model.md](security-model.md)
- [docs/security/SECURITY.md](security/SECURITY.md)
- [docs/setup/DEVELOPMENT.md](setup/DEVELOPMENT.md)
- [docs/testing.md](testing.md)
- [docs/testing/VERIFICATION.md](testing/VERIFICATION.md)
- [reports/2026-07-07-memory-workflow-validation.md](../reports/2026-07-07-memory-workflow-validation.md)

## Workflow Report Locations
- [reports/](../reports/) is for root-level Codex validation and review reports.
- [handoffs/](../handoffs/) is for future handoff notes.
- [docs/reports/](reports/) is for curated documentation reports and historical archives.

## Important Commands Found
- python -m pip install -e . - explicit README command, source: README.md; detail: README documented command
- file-uncorrupter - explicit console script, source: pyproject.toml [project.scripts]; detail: dispatches to file_uncorrupter.cli:main
- file-uncorrupter scan/classify/recover/benchmark/report - explicit CLI command surface, source: README.md and src/file_uncorrupter/cli.py; detail: documented in docs/api/CLI.md
- python -m pytest - explicit README command with pyproject pytest configuration; detail: pytest must be installed in the active Python environment

## Open Unknowns
- Confirm whether pytest should be declared as an optional or development dependency, or remain an externally installed tool.
- Confirm future handoff naming conventions when root handoffs/ starts receiving notes.
- Historical archives under VERSIONS/ and docs/reports/archive/ are preserved as evidence, not authoritative current behavior.
