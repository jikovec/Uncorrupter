# Obsidian And Agent Indexing Plan - 2026-07-09

## Summary

This report plans and records the documentation, Obsidian, repo-indexing, and future-agent orientation system for File Uncorrupter. It is intentionally documentation-only: no source code, tests, package metadata, runtime behavior, release archives, deployment configuration, cloud setup, account setup, or encryption setup should be changed by this work.

File Uncorrupter is an offline-first Python CLI for scanning, classifying, and recovering damaged visual media. The current package uses SQLite evidence tracking, JPEG-focused recovery strategies, baseline image/video carving, optional FFmpeg/ffprobe paths, and JSON/CSV report export.

## Repository Summary

Primary truth sources inspected:

- `README.md`
- `AGENTS.md`
- `00_Index.md`
- `pyproject.toml`
- `.gitignore`
- `.git/info/exclude`
- `docs/`
- `reports/`
- `handoffs/`
- `src/file_uncorrupter/`
- `tests/`

Current source areas:

- `src/file_uncorrupter/cli.py` - CLI parser and command dispatch.
- `src/file_uncorrupter/pipeline.py` - scan, classify, recover, and persistence orchestration.
- `src/file_uncorrupter/intake.py` and `src/file_uncorrupter/signature_index.py` - file intake and signature detection.
- `src/file_uncorrupter/classification.py` - classification labels and evidence.
- `src/file_uncorrupter/engines/` - `jpeg-v1` and `baseline-v2` candidate generation.
- `src/file_uncorrupter/decoders.py` - Pillow and FFmpeg/ffprobe adapters.
- `src/file_uncorrupter/db.py` and `src/file_uncorrupter/reporting.py` - SQLite persistence and exports.
- `src/file_uncorrupter/workspace.py` - local workspace layout and config snapshots.

Current tests:

- `tests/test_classification.py`
- `tests/test_signature_index.py`
- `tests/test_db.py`
- `tests/test_recovery.py`

Known uncertainties:

- `pyproject.toml` declares version `0.3.0`, while `src/file_uncorrupter/__init__.py` exposes `__version__ = "0.2.0"`.
- `pytest` is configured but is not declared as a package dependency.
- FFmpeg/ffprobe availability is local environment dependent.
- Historical archives under `VERSIONS/` and `docs/reports/archive/` are evidence, not current implementation truth.

## Source Of Truth Hierarchy

Use this order when documentation conflicts:

1. Current source, package config, tests, and workflows if added later.
2. `pyproject.toml` and package entry points.
3. `README.md` and current developer docs under `docs/`.
4. Root workflow reports under `reports/` and handoff notes under `handoffs/`.
5. Curated historical docs under `docs/reports/`.
6. Historical release archives under `VERSIONS/`.
7. Clearly marked inferred notes.

Historical reports and release archives must stay preserved, but they should not override current source/config/tests.

## Current Documentation Map

Existing current docs:

- `README.md` - root overview, commands, and quick start.
- `00_Index.md` - Obsidian root hub and project map.
- `AGENTS.md` - memory-first workflow for Codex agents.
- `docs/INDEX.md` - current documentation index.
- `docs/PROJECT-OVERVIEW.md` - package purpose and important paths.
- `docs/setup/DEVELOPMENT.md` - install and local commands.
- `docs/architecture/ARCHITECTURE.md` - module boundaries and data flow.
- `docs/api/CLI.md` - public CLI surface.
- `docs/testing/VERIFICATION.md` - pytest coverage and smoke checks.
- `docs/security/SECURITY.md` - local data handling and decoder risk.
- `docs/releases/CHANGELOG.md` - current version-surface notes.
- `docs/commands.md`, `docs/current-state.md`, `docs/testing.md`, `docs/security-model.md`, and `docs/decisions.md` - memory scaffold notes.
- `docs/reports/INDEX.md` - curated documentation report index.

Missing or weak areas before implementation:

- Dedicated Obsidian usage guide.
- Dedicated future-agent orientation guide.
- Human-readable source map.
- Human-readable docs/source/test/report/handoff connection map.
- Root `reports/INDEX.md` for workflow reports.
- Root `handoffs/INDEX.md` for handoff notes.
- Machine-readable `docs/agent-index.json`.

## Obsidian Readiness

The repo root can be opened as a local Obsidian vault for documentation and working context. The `.obsidian/` directory must remain ignored because it can contain private workspace state, local plugin state, window layout, graph settings, and potentially account or sync metadata if a user configures plugins.

Recommended conventions:

- Keep Obsidian local-first and plaintext.
- Do not add Obsidian Sync, cloud sharing, accounts, encryption setup, or company integrations.
- Use normal Markdown links as canonical so GitHub and code review stay readable.
- Use Obsidian wiki links sparingly in hub pages where backlinks and graph navigation are useful.
- Keep tags small and stable; do not tag every paragraph.
- Do not put secrets, private paths, API keys, tokens, account IDs, or personal data into notes.

## Tag Taxonomy

Global tags:

- `#repo/index`
- `#repo/architecture`
- `#repo/development`
- `#repo/testing`
- `#repo/security`
- `#repo/roadmap`
- `#repo/decision`
- `#repo/source-map`
- `#repo/connection-map`
- `#agent/orientation`
- `#agent/handoff`
- `#agent/report`
- `#obsidian/local`
- `#obsidian/graph`

Repo tags:

- `#uncorrupter/cli`
- `#uncorrupter/recovery`
- `#uncorrupter/jpeg`
- `#uncorrupter/video`
- `#uncorrupter/ffmpeg`
- `#uncorrupter/sqlite`
- `#uncorrupter/evidence`
- `#uncorrupter/signature-detection`
- `#uncorrupter/testing`
- `#uncorrupter/history`
- `#uncorrupter/release-artifacts`

Avoid tags that imply unsupported behavior unless future source/docs implement those capabilities:

- `#repo/cloud`
- `#repo/auth`
- `#repo/encryption`
- `#repo/telemetry`
- `#repo/production-deploy`

## Proposed Complete System

Implemented or planned artifacts:

- Create `reports/obsidian-agent-indexing-plan.md` as the durable planning report.
- Update `AGENTS.md`, `00_Index.md`, `README.md`, `docs/INDEX.md`, and `docs/current-state.md` to route to the new orientation system.
- Update `docs/architecture/ARCHITECTURE.md`, `docs/setup/DEVELOPMENT.md`, `docs/testing/VERIFICATION.md`, `docs/security/SECURITY.md`, `docs/decisions.md`, and `docs/reports/INDEX.md` with cross-links and maintenance guidance.
- Create `docs/OBSIDIAN.md` for local-first vault use.
- Create `docs/AGENT-INDEX.md` for future-agent orientation.
- Create `docs/SOURCE-MAP.md` for source and test mapping.
- Create `docs/CONNECTIONS.md` for source/test/doc/report/handoff links.
- Create `reports/INDEX.md` for root workflow reports.
- Create `handoffs/INDEX.md` for future handoff routing.
- Create `docs/agent-index.json` as the canonical machine-readable index.

Artifacts intentionally omitted:

- `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `docs/SECURITY.md`, and `docs/DECISIONS.md`, because existing nested or lowercase docs already cover those roles.
- `.agents/index.json`, because `.agents/` is local-only Spec Kit scaffolding ignored by `.git/info/exclude`.

## Connection Map Plan

The docs should connect:

- `docs/architecture/ARCHITECTURE.md` to `src/file_uncorrupter/pipeline.py`, `engines/`, `decoders.py`, `db.py`, and `workspace.py`.
- `docs/testing/VERIFICATION.md` to `tests/test_classification.py`, `tests/test_signature_index.py`, `tests/test_db.py`, and `tests/test_recovery.py`.
- `docs/security/SECURITY.md` to `src/file_uncorrupter/decoders.py`, `src/file_uncorrupter/db.py`, and local evidence outputs.
- `docs/AGENT-INDEX.md` to `docs/SOURCE-MAP.md`, `docs/CONNECTIONS.md`, `docs/agent-index.json`, `reports/INDEX.md`, and `handoffs/INDEX.md`.
- `reports/INDEX.md` to root workflow reports and implementation reports.
- `handoffs/INDEX.md` to future notes that explain incomplete or deferred work.

## Machine-Readable Index Schema

`docs/agent-index.json` should include:

- `repo_name`
- `repo_purpose`
- `last_reviewed`
- `primary_languages`
- `frameworks_and_tools`
- `important_paths`
- `docs_entry_points`
- `source_areas`
- `test_areas`
- `commands`
- `report_locations`
- `handoff_locations`
- `decision_locations`
- `safety_rules`
- `sensitive_path_rules`
- `obsidian_conventions`
- `tag_taxonomy`
- `known_risks`
- `omitted_artifacts`

The index should use repo-relative paths only. It must not include secrets, tokens, account identifiers, private URLs, private machine identifiers, or sensitive local paths.

## Implementation Order

1. Re-check `git status --short` and preserve unrelated dirty files.
2. Re-read root memory files, docs, source, tests, `.gitignore`, and `.git/info/exclude`.
3. Create the new docs hubs and indexes.
4. Update root and docs navigation.
5. Add `docs/agent-index.json`.
6. Validate JSON and Markdown links.
7. Run `git diff --check`.
8. Run `python -m pytest` only when pytest is available or installed outside the repo.
9. Verify generated docs are plaintext.
10. Write an implementation report under `reports/`.

## Verification Plan

Safe commands:

```powershell
git status --short
git status --ignored --short
git ls-files
python -m json.tool .\docs\agent-index.json
git diff --check
python -m pytest
```

For this docs-only implementation, full pytest is optional unless Python tooling/config/source files change. If pytest is not available in the active environment, record that exact blocker instead of modifying package metadata.

## Risks And Non-Goals

Do not:

- Change runtime behavior.
- Edit source, tests, package metadata, release archives, deployment config, or generated dependency/build output.
- Delete historical docs or release archives.
- Invent architecture, security guarantees, roadmap items, release status, deployment workflows, auth behavior, encryption, cloud sync, telemetry, or account integrations.
- Track `.obsidian/` settings.
- Track local-only `.agents/` or `.specify/` scaffolding without an explicit future decision.

Human review remains useful for:

- Dirty `VERSIONS/` archive changes.
- The package version mismatch.
- Whether pytest should become an optional/dev dependency.
- Future naming conventions once real handoff notes exist.

## Ready-To-Run Implementation Prompt

Implement the approved Obsidian, documentation, repo-indexing, and future-agent orientation system for this repository using this report as the source. Re-check repo state before editing. Prefer the complete artifact set when valid, but omit, merge, or leave unchanged any artifact that is redundant, harmful, stale, ignored by repo convention, or inconsistent with current source/docs, and document the reason. Preserve runtime behavior. Do not edit source, tests, package metadata, release archives, deploy config, cloud/account settings, encryption setup, or secrets. Keep Obsidian local-first and plaintext. Add/update human-readable docs, `docs/agent-index.json`, source/test/doc/report/handoff connections, root report and handoff indexes, and the repo-specific tag taxonomy. Run safe verification, then produce a final implementation report. Do not commit, push, deploy, publish, tag, or release.
