<!-- codex-memory-scaffold:testing -->
# Testing

## Explicit Or Discovered Test And Check Commands
- python -m pytest - explicit README command with pyproject pytest configuration; detail: pytest must be installed in the active Python environment

## Inferred Commands
- No separate inferred test command is needed; pyproject.toml configures pytest with `pythonpath = ["src"]` and `testpaths = ["tests"]`.

## Verification Notes
- Commands listed as explicit were discovered in project files.
- Commands listed as inferred need maintainer confirmation before they are treated as authoritative.
- pytest is configured but not declared as a runtime dependency. Install it in the active environment or an isolated temporary dependency location before relying on `python -m pytest`.
- FFmpeg-dependent tests are expected to skip automatically when FFmpeg is not available.
- No tests were run during the original Obsidian/memory scaffolding pass; see [reports/2026-07-07-memory-workflow-validation.md](../reports/2026-07-07-memory-workflow-validation.md) for the follow-up memory validation pass.
