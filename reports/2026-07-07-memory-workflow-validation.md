# Memory Workflow Validation - 2026-07-07

## Scope

Validated the repo-root Codex project memory workflow against the current repository tree. This pass did not edit application source code, move files, rename files, delete files, commit, or push.

## Memory Files Checked

- [AGENTS.md](../AGENTS.md)
- [00_Index.md](../00_Index.md)
- [docs/current-state.md](../docs/current-state.md)
- [docs/decisions.md](../docs/decisions.md)
- [docs/commands.md](../docs/commands.md)
- [docs/testing.md](../docs/testing.md)
- [docs/security-model.md](../docs/security-model.md)

Related docs and reports checked for comparison:

- [README.md](../README.md)
- [pyproject.toml](../pyproject.toml)
- [docs/INDEX.md](../docs/INDEX.md)
- [docs/PROJECT-OVERVIEW.md](../docs/PROJECT-OVERVIEW.md)
- [docs/setup/DEVELOPMENT.md](../docs/setup/DEVELOPMENT.md)
- [docs/architecture/ARCHITECTURE.md](../docs/architecture/ARCHITECTURE.md)
- [docs/api/CLI.md](../docs/api/CLI.md)
- [docs/testing/VERIFICATION.md](../docs/testing/VERIFICATION.md)
- [docs/security/SECURITY.md](../docs/security/SECURITY.md)
- [docs/reports/INDEX.md](../docs/reports/INDEX.md)
- [docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md](../docs/reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md)

## Accurate

- Project purpose, package shape, Python requirement, package dependency, and optional FFmpeg notes match README.md, pyproject.toml, and current docs.
- CLI command names and common arguments match the parser in src/file_uncorrupter/cli.py.
- Testing guidance points at pytest, matching README.md and pyproject.toml pytest configuration.
- Security memory correctly describes a local/offline CLI, local evidence outputs, FFmpeg subprocess risk, and unsupported security properties.
- Version-surface mismatch is documented accurately: pyproject.toml declares 0.3.0 while src/file_uncorrupter/__init__.py declares 0.2.0.
- Historical docs and release artifacts are identified as evidence rather than current implementation truth.

## Corrected

- Fixed stale relative Markdown links in docs/current-state.md, docs/security-model.md, and docs/architecture.md.
- Fixed the 00_Index.md maintenance typo that pointed future reports to `eports/`.
- Added root reports/ and handoffs/ references to 00_Index.md and docs/current-state.md.
- Added this root reports/ validation note as the current workflow validation artifact.
- Added the pyproject-declared `file-uncorrupter` console script and current CLI subcommands to docs/commands.md and docs/current-state.md.
- Clarified that pytest is configured but not declared as a package dependency, so it must exist in the active environment before running `python -m pytest`.

## Unknown

- Whether pytest should be added as an optional or development dependency is a product/maintainer decision.
- Root handoffs/ currently has no notes, so future naming conventions still need to emerge.
- FFmpeg availability on each future workstation remains environment-specific.
- Historical archives under VERSIONS/ and docs/reports/archive/ were inventoried, not revalidated line by line.

## Readiness

The repo is ready for future Codex work using the memory-first workflow. The memory files now give a useful entry path, link to the current docs and root workflow report locations, identify source-of-truth boundaries, list the key commands, and preserve unknowns instead of inventing decisions.

## Verification

- Direct `python -m pytest -p no:cacheprovider` initially failed because the active Python 3.11.9 environment did not have pytest installed.
- Pillow was already available in the active Python environment.
- Installed pytest 9.1.1 into `%TEMP%\codex-uncorrupter-pytest-deps`, outside the repo.
- Re-ran with `PYTHONPATH` set to `%TEMP%\codex-uncorrupter-pytest-deps;src`, `PYTHONDONTWRITEBYTECODE=1`, and pytest cache disabled.
- Result: `14 passed, 1 skipped`.
- Markdown link check over 21 Markdown files passed.
- Obsidian wiki-link check over 21 Markdown files passed.
