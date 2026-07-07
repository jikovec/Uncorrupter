# Documentation Index

This index is the entry point for current documentation. The repository code, tests, and package metadata are the source of truth when a historical report disagrees with the current implementation.

## Start Here

- [Project overview](PROJECT-OVERVIEW.md) - what the package does now and where the important files live.
- [Developer setup](setup/DEVELOPMENT.md) - install, optional FFmpeg setup, and local development commands.
- [Architecture](architecture/ARCHITECTURE.md) - current module boundaries and data flow.
- [CLI reference](api/CLI.md) - commands, options, outputs, and the note that there is no HTTP route layer.

## Operational Docs

- [Security and local data handling](security/SECURITY.md)
- [Testing and verification](testing/VERIFICATION.md)
- [Changelog and release notes](releases/CHANGELOG.md)

## Reports And Archive

- [Reports index](reports/INDEX.md)
- [Historical research blueprint](reports/archive/001-deep-research-report.md)
- [Documentation reorganization report](reports/DOCUMENTATION-REORGANIZATION-2026-07-07.md)

## Current Documentation Inventory

Current, developer-facing docs:

- [README.md](../README.md)
- [docs/INDEX.md](INDEX.md)
- [docs/PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md)
- [docs/setup/DEVELOPMENT.md](setup/DEVELOPMENT.md)
- [docs/architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md)
- [docs/api/CLI.md](api/CLI.md)
- [docs/security/SECURITY.md](security/SECURITY.md)
- [docs/testing/VERIFICATION.md](testing/VERIFICATION.md)
- [docs/releases/CHANGELOG.md](releases/CHANGELOG.md)
- [docs/reports/INDEX.md](reports/INDEX.md)

Historical or evidence docs:

- [docs/reports/archive/001-deep-research-report.md](reports/archive/001-deep-research-report.md)
- [VERSIONS/](../VERSIONS/) contains historical archives and legacy release artifacts.

Empty or non-canonical documentation locations found during inventory:

- `CHANGELOG/` existed as a top-level directory but contained no tracked files during this cleanup.
- `results/` existed as a top-level directory but contained no tracked files during this cleanup.
- `DOCUMENTATION/` previously contained the deep research report; that report now lives in the report archive.
