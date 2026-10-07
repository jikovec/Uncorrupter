# Connection Map

Tags: #repo/connection-map #agent/orientation #uncorrupter/evidence

This map explains how current docs, source, tests, reports, and handoffs should point at each other. Keep it updated when module boundaries, docs hubs, report locations, or handoff practices change.

## Docs To Source

- [Architecture](architecture/ARCHITECTURE.md) should stay connected to [cli.py](../src/file_uncorrupter/cli.py), [pipeline.py](../src/file_uncorrupter/pipeline.py), [engines](../src/file_uncorrupter/engines/), [decoders.py](../src/file_uncorrupter/decoders.py), [db.py](../src/file_uncorrupter/db.py), and [workspace.py](../src/file_uncorrupter/workspace.py).
- [CLI reference](api/CLI.md) should stay connected to [cli.py](../src/file_uncorrupter/cli.py) and the console script declaration in [pyproject.toml](../pyproject.toml).
- [Security](security/SECURITY.md) should stay connected to [decoders.py](../src/file_uncorrupter/decoders.py), [db.py](../src/file_uncorrupter/db.py), local evidence outputs, and the unsupported security properties list.
- [Testing](testing/VERIFICATION.md) should stay connected to [pyproject.toml](../pyproject.toml) and all current files under [tests](../tests/).
- [Source map](SOURCE-MAP.md) should stay connected to every current source/test area.

## Source To Tests

- CLI behavior in [cli.py](../src/file_uncorrupter/cli.py) is indirectly covered through recovery and DB-oriented tests; add direct CLI tests if command parsing changes.
- Intake, signature detection, and kind detection in [intake.py](../src/file_uncorrupter/intake.py), [signature_index.py](../src/file_uncorrupter/signature_index.py), and [constants.py](../src/file_uncorrupter/constants.py) connect to [test_signature_index.py](../tests/test_signature_index.py) and classification/recovery tests.
- Classification in [classification.py](../src/file_uncorrupter/classification.py) connects to [test_classification.py](../tests/test_classification.py).
- Candidate engines under [engines](../src/file_uncorrupter/engines/) connect to [test_recovery.py](../tests/test_recovery.py).
- SQLite persistence in [db.py](../src/file_uncorrupter/db.py) connects to [test_db.py](../tests/test_db.py).
- Decoder behavior in [decoders.py](../src/file_uncorrupter/decoders.py) connects to [test_recovery.py](../tests/test_recovery.py), with FFmpeg-dependent checks skipped when local tools are unavailable.

## Reports To Implemented Changes

Root reports under [reports](../reports/) should capture validation, implementation evidence, and workflow-specific findings. The root [reports index](../reports/INDEX.md) is the routing surface for these notes.

Curated documentation reports under [docs/reports](reports/) preserve documentation reorganizations and historical research. The [curated reports index](reports/INDEX.md) should link archived research and documentation cleanup reports.

When a report changes the current understanding of the repo, update:

- [current-state.md](current-state.md)
- [AGENT-INDEX.md](AGENT-INDEX.md)
- [SOURCE-MAP.md](SOURCE-MAP.md)
- [agent-index.json](agent-index.json)

## Handoffs To Remaining Work

Use [handoffs](../handoffs/) for notes that a later agent should act on. Keep [handoffs/INDEX.md](../handoffs/INDEX.md) current when adding a handoff.

A handoff should include:

- date
- scope
- current state
- exact files touched or inspected
- blockers
- recommended next commands
- risks and non-goals

## Workflows And Verification

Supported current checks:

- `python -m json.tool .\docs\agent-index.json`
- `git diff --check`
- `python -m pytest`

`python -m pytest` depends on pytest being installed in the active environment. If it is unavailable, record the blocker rather than changing dependencies during a docs-only pass.

There is no documented deployment workflow in this repo. Do not add deployment docs that imply production deploy support.

## Decisions And Roadmap

- [decisions.md](decisions.md) is the current decision log placeholder.
- [docs/reports/archive/001-deep-research-report.md](reports/archive/001-deep-research-report.md) contains historical research and roadmap-like ideas, but those are not current product commitments.
- Add future ADRs or decision notes only when a real repo decision is made.

## Machine-Readable Index

[agent-index.json](agent-index.json) mirrors this map in a compact format for agents and scripts. Keep it repo-relative and free of secrets, private local paths, account identifiers, private URLs, and personal data.

## Agent toolkit connections

[Project identity](../.agent/project.yaml) → [root instructions](../AGENTS.md) →
[canonical workflows](../skills/) → [shared project processes](../.agent/workflows/README.md).
Native adapters point to canonical skills; [routing cases](../.agent/evals/skill-routing.md)
and [structural validation](../.agent/hooks/README.md) check different properties.
Policy adoption is recorded in [decisions](decisions.md); observed delivery evidence
belongs in the [bootstrap handoff](../handoffs/2026-10-07-agent-toolkit.md).
