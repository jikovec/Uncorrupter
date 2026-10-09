# Documentation Index

The documentation describes the current `0.4.0` source candidate. Source, package metadata, tests, and executable capabilities override stale narrative or historical archives.

## Start Here

- [Current state](current-state.md)
- [Executable capability baseline](capabilities.generated.md)
- [Capabilities, format depth, and roadmap](CAPABILITIES-AND-ROADMAP.md)
- [Benchmark ground-truth schema and metrics](BENCHMARK-GROUND-TRUTH.md)
- [Project overview](PROJECT-OVERVIEW.md)
- [CLI reference](api/CLI.md)
- [Security and local data handling](security/SECURITY.md)
- [Testing and verification](testing/VERIFICATION.md)

## Maintainer Orientation

- [Agent index](AGENT-INDEX.md)
- [Machine-readable agent index](agent-index.json)
- [Architecture](architecture/ARCHITECTURE.md)
- [Source map](SOURCE-MAP.md)
- [Connection map](CONNECTIONS.md)
- [Decisions](decisions.md)
- [Developer setup](setup/DEVELOPMENT.md)
- [Commands](commands.md)
- [Changelog and candidate release notes](releases/CHANGELOG.md)

## Current Reports And Handoffs

- [Stabilized multi-format implementation](../reports/2026-08-05-stabilized-multiformat-implementation.md)
- [Stabilized multi-format handoff](../handoffs/2026-08-05-stabilized-multiformat-recovery.md)
- [Pre-stabilization assessment](../reports/2026-07-26-current-state-and-roadmap-assessment.md)
- [Video/JPEG classification handoff](../handoffs/2026-07-26-video-jpeg-misclassification-fix.md)
- [Root reports index](../reports/INDEX.md)
- [Handoffs index](../handoffs/INDEX.md)
- [Curated/historical reports index](reports/INDEX.md)

## Local Obsidian

- [Obsidian local-vault guide](OBSIDIAN.md)
- Repository root hub: [00_Index.md](../00_Index.md)

`.obsidian/` is ignored local state. Documentation is canonical as normal Markdown and must not depend on cloud sync, accounts, or editor-specific metadata.

## Historical And Secondary Docs

- `docs/reports/archive/` contains historical research.
- `VERSIONS/`, root `CHANGELOG/`, `DOCUMENTATION/`, and `results/` are retained historical/project artifacts.
- Historical files can explain earlier design stages but do not override current behavior.

## Documentation Maintenance Rules

- Capability claims must match registered handlers and `docs/capabilities.generated.md`.
- Local tests must be labeled local/synthetic; workflow definitions are not remote CI proof.
- No deployment/release claim without action and confirmation.
- Keep commands executable and paths relative.
- Update `agent-index.json` with path, command, tag, safety, capability, and risk changes.
- Add a dated report and handoff after substantive implementation.
- Preserve user-authored `OBSIDIAN.md` changes unless the task specifically covers them.
