# Changelog And Release Notes

This page records current release and version documentation from the repo. It does not replace package metadata.

## Current Version Surfaces

- [pyproject.toml](../../pyproject.toml) declares package version `0.3.0`.
- [src/file_uncorrupter/__init__.py](../../src/file_uncorrupter/__init__.py) declares `__version__ = "0.2.0"`.
- The mismatch is intentionally documented here because changing it would be a runtime/source change.

Use [pyproject.toml](../../pyproject.toml) as the package metadata source until the runtime `__version__` surface is reconciled in a code change.

## Current Capability Notes

Current docs describe the repo state after the modular package shape was introduced:

- CLI commands for scan, classify, recover, benchmark, and report.
- Evidence-rich SQLite schema for runs, files, signatures, candidates, attempts, outputs, and frames.
- `baseline-v2` as the default engine.
- `jpeg-v1` as the deepest implemented repair engine.
- Optional FFmpeg/ffprobe video and image fallback paths.
- JSON and CSV report export.

## Historical Version Artifacts

The [VERSIONS/](../../VERSIONS/) directory contains historical artifacts. At documentation inventory time, the current filesystem showed:

- `Uncorrupter alfa 0.1.0.py`
- `Uncorrupter v0.1.1.zip`
- `Uncorrupter v0.1.2.zip`
- `Uncorrupter v0.1.3.zip`

These archives are preserved as evidence. They are not the canonical source for current implementation behavior.

## Git History Snapshot

Recent commit subjects observed during this cleanup:

- `v0.1.3`
- `repo structure`
- `backup`
- `v 0.1.0`
- `v0.0.1`
- `Initial commit`

This is a history snapshot, not a generated release note. Prefer tagged releases or package metadata if they are added later.
