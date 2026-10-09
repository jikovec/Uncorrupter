# Uncorrupter

Tags: #repo/index #uncorrupter/recovery #uncorrupter/evidence #obsidian/local

File Uncorrupter `0.4.0` is a local, bounded, evidence-preserving recovery CLI for damaged text, archives, documents, PDF, images, audio, and video containers. Support depth is operation-specific; start with executable capabilities and current evidence rather than historical extension lists.

## Start Here

1. [Repository instructions](AGENTS.md)
2. [Current state](docs/current-state.md)
3. [Executable capability baseline](docs/capabilities.generated.md)
4. [Capabilities and roadmap](docs/CAPABILITIES-AND-ROADMAP.md)
5. [Benchmark ground-truth schema](docs/BENCHMARK-GROUND-TRUTH.md)
6. [Architecture](docs/architecture/ARCHITECTURE.md)
7. [Agent orientation](docs/AGENT-INDEX.md)
8. [Source map](docs/SOURCE-MAP.md)
9. [Connection map](docs/CONNECTIONS.md)

- [Current project card](docs/PROJECT-OVERVIEW.md#current-project-card--2026-09-09)
- [Project AI workflow](docs/agent-workflow.md)
- [2026-09-09 orientation handoff](handoffs/2026-09-09-local-orientation.md)

## User Documentation

- [README](README.md)
- [Project overview](docs/PROJECT-OVERVIEW.md)
- [CLI reference](docs/api/CLI.md)
- [Benchmark ground-truth schema and metrics](docs/BENCHMARK-GROUND-TRUTH.md)
- [Security and local data handling](docs/security/SECURITY.md)
- [Testing and verification](docs/testing/VERIFICATION.md)
- [Developer setup](docs/setup/DEVELOPMENT.md)
- [Commands](docs/commands.md)
- [Changelog and candidate release notes](docs/releases/CHANGELOG.md)

## Architecture And Decisions

- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Decisions](docs/decisions.md)
- [Source map](docs/SOURCE-MAP.md)
- [Connection map](docs/CONNECTIONS.md)
- [Machine-readable agent index](docs/agent-index.json)

## Current Evidence

- [Stabilized multi-format implementation report](reports/2026-08-05-stabilized-multiformat-implementation.md)
- [Stabilized multi-format handoff](handoffs/2026-08-05-stabilized-multiformat-recovery.md)
- [Pre-stabilization current-state/roadmap assessment](reports/2026-07-26-current-state-and-roadmap-assessment.md)
- [Declared-video/embedded-JPEG classification handoff](handoffs/2026-07-26-video-jpeg-misclassification-fix.md)
- [Reports index](reports/INDEX.md)
- [Handoffs index](handoffs/INDEX.md)

## Runtime Map

```text
CLI
  -> layout/config/capability checks
  -> deterministic intake and immutable byte source
  -> signatures and independent classification evidence
  -> registered handler inspect / explicit goal plan / execute
  -> bounded optional tools and atomic artifacts
  -> SQLite schema v2 plus JSONL events
  -> JSON/CSV/text/benchmark reports
```

Primary source areas:

- `src/file_uncorrupter/cli.py`
- `src/file_uncorrupter/pipeline.py`
- `src/file_uncorrupter/handlers/`
- `src/file_uncorrupter/byte_source.py`
- `src/file_uncorrupter/budgets.py`
- `src/file_uncorrupter/atomic.py`
- `src/file_uncorrupter/process_runner.py`
- `src/file_uncorrupter/db.py`
- `src/file_uncorrupter/reporting.py`
- `src/file_uncorrupter/benchmarking.py`
- `tests/`

## Primary Commands

```powershell
python -m pip install -e ".[dev]"
file-uncorrupter capabilities --format json
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
file-uncorrupter classify .\input --recursive --all-files --db .\runs.sqlite3
file-uncorrupter recover .\input .\output --recursive --all-files --goal repair --goal extract --db .\runs.sqlite3
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
python -m pytest -p no:cacheprovider -q
python -m build
```

## Authority And Boundaries

- Current source, `pyproject.toml`, tests, and executable capabilities outrank historical docs/release archives.
- Local green tests are not CI execution, deployment, release, or broad corpus proof.
- Recovery outputs/databases/reports can contain private data and are not public by default.
- Input files are immutable; output paths are separate, contained, atomic, and no-clobber by default.
- Optional tools do not grant permission, safety, or full-fidelity support.
- No Git staging, commit, push, PR, workflow dispatch, publication, release, or deployment occurs without explicit action-specific authorization.

## Local-Only Notes

- [Obsidian guide](docs/OBSIDIAN.md) documents a local-first plaintext vault; `.obsidian/` remains ignored.
- `.agents/` and `.specify/` remain local-only workflow scaffolding.
- `.uncorrupter-workspace/`, `output/`, `single-input/`, databases, and reports are local evidence/generated material.
- `VERSIONS/`, `CHANGELOG/`, `DOCUMENTATION/`, and archived reports are historical evidence, not current runtime authority.

## Maintenance

When paths, commands, capabilities, safety rules, or known risks change, update the executable tests, generated capability baseline, relevant narrative docs, `docs/agent-index.json`, and a dated report/handoff. Preserve existing user-owned and unrelated dirty worktree changes.
