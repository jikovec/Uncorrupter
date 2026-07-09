# Future-Agent Orientation

Tags: #agent/orientation #repo/index #uncorrupter/recovery

This is the start-here workflow for future Codex runs and other repo agents. It summarizes where to begin, which files are authoritative, what must not be changed casually, and how to keep documentation and project memory current.

## Start Here

Read in this order before meaningful work:

1. [AGENTS.md](../AGENTS.md)
2. [Root vault index](../00_Index.md)
3. [Current state](current-state.md)
4. [Decisions](decisions.md)
5. [Documentation index](INDEX.md)
6. [Project overview](PROJECT-OVERVIEW.md)
7. [Source map](SOURCE-MAP.md)
8. [Connection map](CONNECTIONS.md)
9. [Commands](commands.md)
10. [Testing notes](testing.md)

For report and handoff context:

- [Root reports index](../reports/INDEX.md)
- [Root handoffs index](../handoffs/INDEX.md)
- [Curated documentation reports](reports/INDEX.md)

Machine-readable orientation:

- [agent-index.json](agent-index.json)

## Source Of Truth

Use this truth order when files disagree:

1. Current source, package config, tests, and workflows if added later.
2. `pyproject.toml` and package entry points.
3. `README.md` and current developer docs under `docs/`.
4. Root workflow reports under `reports/` and handoffs under `handoffs/`.
5. Curated historical docs under `docs/reports/`.
6. Historical release artifacts under `VERSIONS/`.
7. Clearly marked inferred notes.

Current implementation facts should come from `src/file_uncorrupter/`, `tests/`, and `pyproject.toml`, not from historical archives.

## Safety Rules

- Preserve existing runtime behavior unless the user explicitly asks for a behavior change.
- Do not edit release archives under `VERSIONS/` unless explicitly asked.
- Do not commit, push, deploy, publish, tag, release, reset, stash, or discard changes unless explicitly asked.
- Do not add secrets, credentials, private keys, tokens, account IDs, private URLs, private certificates, or `.env` contents to docs.
- Do not claim encryption, auth, telemetry, cloud sync, sandboxing, secure deletion, or deployment support unless current source/docs implement it.
- Keep `.obsidian/`, `.agents/`, and `.specify/` local-only unless a future explicit decision changes that.

## Current Product Shape

File Uncorrupter is an offline-first Python CLI. Public commands are defined in [src/file_uncorrupter/cli.py](../src/file_uncorrupter/cli.py):

- `scan`
- `classify`
- `recover`
- `benchmark`
- `report`

The console script is declared in [pyproject.toml](../pyproject.toml) as `file-uncorrupter = "file_uncorrupter.cli:main"`.

There is no HTTP API, route layer, authentication system, deployment workflow, or remote service integration in the current repo.

## Update Obligations

After meaningful repo changes:

- Update [current-state.md](current-state.md) when package purpose, commands, source areas, docs, reports, or open unknowns change.
- Update [SOURCE-MAP.md](SOURCE-MAP.md) when source/test areas or module responsibilities change.
- Update [CONNECTIONS.md](CONNECTIONS.md) when docs/source/test/report/handoff links change.
- Update [agent-index.json](agent-index.json) when paths, commands, safety rules, tags, or known risks change.
- Add a report under `reports/` for durable validation, review, or implementation evidence.
- Add a note under `handoffs/` when work is intentionally deferred or a future agent needs context.

## Common Verification

Use the smallest check set that matches the work:

```powershell
git status --short
python -m json.tool .\docs\agent-index.json
git diff --check
python -m pytest
```

`python -m pytest` requires pytest in the active environment. If pytest is unavailable, record the exact blocker instead of changing package metadata during a docs-only task.

## Known Risks

- The worktree may contain unrelated dirty release archive changes under `VERSIONS/`.
- `pyproject.toml` currently declares `0.3.0`, while `src/file_uncorrupter/__init__.py` exposes `__version__ = "0.2.0"`.
- FFmpeg/ffprobe-dependent behavior and tests depend on local tool availability.
- Historical reports can contain future-looking or stale claims; treat them as evidence, not current truth.
