# Current-State And Roadmap Assessment - 2026-07-26

Tags: #agent/report #repo/roadmap #uncorrupter/evidence

## Outcome

Documented File Uncorrupter's implemented capabilities, current maturity, stabilization needs, concrete target foundation, and expansion possibilities for images, video, documents, archives, TXT, Markdown, and related formats.

The canonical result is [Capabilities, Stabilization, And File-Format Roadmap](../docs/CAPABILITIES-AND-ROADMAP.md).

## Evidence Boundary

Current source, tests, and `pyproject.toml` were treated as authoritative. Existing docs and historical research were used for context only and corrected where they overstated current format support.

At the start of this task, the worktree was on `main` at `70fd118`. The only pre-existing dirty path was `docs/OBSIDIAN.md`; that user-owned change was inspected for overlap and left untouched.

No application source, tests, package metadata, release archives, generated recovery output, deployment configuration, or Obsidian local settings were changed.

## Inspected Project Documentation

- `AGENTS.md`
- `00_Index.md`
- `README.md`
- `docs/current-state.md`
- `docs/decisions.md`
- `docs/AGENT-INDEX.md`
- `docs/SOURCE-MAP.md`
- `docs/CONNECTIONS.md`
- `docs/agent-index.json`
- `docs/INDEX.md`
- `docs/PROJECT-OVERVIEW.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/api/CLI.md`
- `docs/setup/DEVELOPMENT.md`
- `docs/testing/VERIFICATION.md`
- `docs/security/SECURITY.md`
- `docs/releases/CHANGELOG.md`
- `reports/INDEX.md`
- `reports/2026-07-07-memory-workflow-validation.md`
- `reports/obsidian-agent-indexing-audit-2026-07-09.md`
- `handoffs/INDEX.md`
- `docs/reports/archive/001-deep-research-report.md` by targeted topic search

## Inspected Implementation Evidence

- `pyproject.toml`
- all current modules under `src/file_uncorrupter/`, excluding the retained legacy implementation as a behavior source
- all collected tests under `tests/test_*.py`
- current Git status and recent commit subjects
- current `results/`, `DOCUMENTATION/`, and `CHANGELOG/` inventories

## Main Findings

- The modular pipeline and evidence database are a strong foundation worth extending.
- JPEG is the only format family with deep repair strategies and focused regression coverage.
- Other mapped images have generic full-file/signature-offset candidates; they do not have format-deep repair tests.
- Video support is FFmpeg-assisted offset carving/remux/preview/frame extraction, with one narrow MP4 recovery test.
- HEIF, AVIF, JP2, and RAW appear in family/extension lists, but the current image writer has no output mapping for them.
- PDF, Office/OpenDocument packages, ZIP/TAR/7z/RAR, TXT, Markdown, CSV, JSON, XML, and HTML have no current handler.
- `--all-files` expands intake only; it does not supply recovery for unknown families.
- Whole-file reads and in-memory candidate payloads are the primary scalability problem.
- Output collision/no-clobber policy, atomic writes, run lifecycle, resource budgets, and final video exception handling need stabilization.
- Package metadata reports `0.3.0` while runtime `__version__` reports `0.2.0`.
- Pytest is configured but not declared as a development dependency, and no CI workflow or maintained benchmark corpus was found.

## Live Verification

The active Python environment initially returned:

```text
No module named pytest
```

Pytest 9.1.1 was installed into a temporary directory outside the repository. The suite was then run with the source and temporary dependency paths, bytecode disabled, and pytest cache disabled.

Result:

```text
platform win32 -- Python 3.11.9
collected 15 items
15 passed in 7.57s
```

The FFmpeg-gated test ran rather than skipping. The installed tool reported FFmpeg `8.1.2-full_build-www.gyan.dev`. Source-path inspection reported Pillow `12.2.0`, package metadata `0.3.0`, and runtime `__version__` `0.2.0`.

This is narrow synthetic-corpus proof. Real-world recovery rate, large-file performance, hostile-input resistance, cross-platform behavior, and most configured formats remain unverified.

## External Reference Refresh

Official documentation was checked for proposed, not implemented, format paths:

- Python `zipfile` and `tarfile` for archive validation/extraction behavior and safety boundaries
- Microsoft Open XML documentation for ZIP/XML package parts and relationships
- Pillow format documentation for current image codec possibilities
- FFmpeg format documentation for demuxer/error controls
- qpdf documentation for heuristic damaged-PDF cross-reference recovery

These references support roadmap feasibility. They do not add dependencies or implementation support to the repository.

## Remaining Work

All implementation work in the roadmap remains proposed. The first recommended product increment is stabilization and a generic handler/resource model, followed by a vertical slice for text plus ZIP/package recovery.

No commit, push, tag, release, or deployment was performed.
