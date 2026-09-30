# Documentation Index

This is the entry point for current repository documentation. Current source, tests, package configuration, and live repository state outrank historical reports and release archives when they disagree.

## Start Here

- [Project overview](PROJECT-OVERVIEW.md)
- [Agent orientation](AGENT-INDEX.md)
- [Source map](SOURCE-MAP.md)
- [Connection map](CONNECTIONS.md)
- [Current state](current-state.md)
- [Decision log](decisions.md)
- [Obsidian local vault guide](OBSIDIAN.md)

## Development And Operation

- [Developer setup](setup/DEVELOPMENT.md)
- [Architecture](architecture/ARCHITECTURE.md)
- [CLI reference](api/CLI.md)
- [Testing and verification](testing/VERIFICATION.md)
- [Security and local data handling](security/SECURITY.md)
- [Changelog and release notes](releases/CHANGELOG.md)
- [Discovered commands](commands.md)

## Repository Policies

- [Contributing](../CONTRIBUTING.md)
- [Security reporting](../SECURITY.md)
- [Support](../SUPPORT.md)
- [Apache License 2.0](../LICENSE)
- [Agent rules](../AGENTS.md)

## Machine-Readable Orientation

- [agent-index.json](agent-index.json)

## Reports, Handoffs, And History

- [Root reports index](../reports/INDEX.md)
- [Root handoffs index](../handoffs/INDEX.md)
- [Curated documentation reports](reports/INDEX.md)
- [Historical research blueprint](reports/archive/001-deep-research-report.md)
- [Historical release artifacts](../VERSIONS/)

The following are historical provenance, not current tracked root directories:

- root `CHANGELOG/`
- root `DOCUMENTATION/`
- root `results/`

The former `DOCUMENTATION/` research report is preserved under `docs/reports/archive/`.

## Canonical Documentation Rule

Do not create parallel root or `docs/` copies when a canonical document already exists. In particular:

- architecture: `docs/architecture/ARCHITECTURE.md`
- development: `docs/setup/DEVELOPMENT.md`
- testing: `docs/testing/VERIFICATION.md`
- security model: `docs/security/SECURITY.md`
- decisions: `docs/decisions.md`

Conventional root files such as `SECURITY.md`, `CONTRIBUTING.md`, and `SUPPORT.md` may exist for GitHub discovery and repository policy; they should route to deeper canonical docs instead of duplicating them.
