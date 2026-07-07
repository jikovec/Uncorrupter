# Documentation Reorganization Report - 2026-07-07

## Scope

This pass reorganized documentation only. No source or runtime behavior files were intentionally changed.

## Files Changed

- [../../README.md](../../README.md)
- [../INDEX.md](../INDEX.md)
- [../PROJECT-OVERVIEW.md](../PROJECT-OVERVIEW.md)
- [../setup/DEVELOPMENT.md](../setup/DEVELOPMENT.md)
- [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- [../api/CLI.md](../api/CLI.md)
- [../security/SECURITY.md](../security/SECURITY.md)
- [../testing/VERIFICATION.md](../testing/VERIFICATION.md)
- [../releases/CHANGELOG.md](../releases/CHANGELOG.md)
- [INDEX.md](INDEX.md)
- [archive/001-deep-research-report.md](archive/001-deep-research-report.md)
- [DOCUMENTATION-REORGANIZATION-2026-07-07.md](DOCUMENTATION-REORGANIZATION-2026-07-07.md)

## Files Moved Or Renamed

- `DOCUMENTATION/001 deep-research-report.md` moved to [archive/001-deep-research-report.md](archive/001-deep-research-report.md).

## Docs Extended

- Root README now points to the docs index and gives a concise current-state overview.
- New docs index groups docs by project overview, setup/development, architecture, CLI/API, security, testing, releases, and reports/archive.
- Project overview documents package metadata, supported families in code, important source paths, and the known version-surface mismatch.
- Developer setup documents Python requirements, editable install, optional FFmpeg behavior, local commands, and generated files.
- Architecture documents current module boundaries, data flow, engines, decoders, scoring, persistence, and workspace behavior.
- CLI reference documents the actual command surface from `src/file_uncorrupter/cli.py` and states that there is no HTTP route layer.
- Security docs document local file handling, untrusted media considerations, FFmpeg subprocess risk, evidence/privacy notes, and unsupported security properties.
- Testing docs document the pytest command and current test coverage by file.
- Changelog/release notes document current version surfaces, capability notes, historical artifacts, and recent git history subjects.

## Docs Archived

- The historical master research and architecture blueprint was kept intact and moved under `docs/reports/archive/`.
- An archive note was added to clarify that the report is historical evidence and that current source/tests/docs should be preferred for implementation facts.
- Existing trailing whitespace in the archived report was stripped mechanically without changing wording.

## Inventory Findings

- Existing documentation before this pass was limited to `README.md` and `DOCUMENTATION/001 deep-research-report.md`.
- Top-level `CHANGELOG/` and `results/` directories existed but contained no tracked files during inventory.
- `VERSIONS/` contains historical release artifacts and was preserved.
- A package version mismatch exists: `pyproject.toml` declares `0.3.0`, while `src/file_uncorrupter/__init__.py` declares `0.2.0`. This was documented, not changed.
- Current code contains no HTTP API or routes; the API documentation therefore covers the CLI surface.

## Validation Commands Run

Initial test command:

```powershell
python -m pytest
```

Result:

```text
failed: No module named pytest
```

Temporary test dependency setup outside the repo:

```powershell
$deps = Join-Path $env:TEMP 'codex-uncorrupter-testdeps'
python -m pip install --target $deps pytest .
$env:PYTHONPATH = "$deps;src"
python -m pytest
```

Result:

```text
14 passed, 1 skipped
```

Markdown link check:

```powershell
<local PowerShell Markdown link resolver over README.md and docs/**/*.md>
```

Result:

```text
Markdown link check passed for 12 files.
```

Markdown whitespace check:

```powershell
<local PowerShell trailing-whitespace check over README.md and docs/**/*.md>
```

Result:

```text
Markdown whitespace check passed for 12 files.
```

## Intentionally Left Unchanged

- No `src/` runtime files were edited.
- No tests were edited.
- No release archives under `VERSIONS/` were edited by this documentation pass.
- Pre-existing worktree changes under `VERSIONS/` were left untouched.
- Empty top-level directories were left alone.
- The `pyproject.toml` and `__init__.py` version mismatch was documented instead of corrected because correcting it would change source/runtime behavior.
