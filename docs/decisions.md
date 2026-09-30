# Decisions

This log records repository decisions that should remain stable across future agent and contributor work. Product behavior decisions belong here only when they are actually accepted.

### 2026-09-30 - Canonical documentation and repository-policy layout

- Context: The repository had mature nested canonical docs plus older same-topic scaffold stubs and stale path claims. The repository-quality baseline also required GitHub-discoverable community/security entry points without duplicating the canonical documentation.
- Decision:
  - Keep `docs/architecture/ARCHITECTURE.md`, `docs/setup/DEVELOPMENT.md`, `docs/testing/VERIFICATION.md`, and `docs/security/SECURITY.md` as canonical subject documents.
  - Use root `SECURITY.md`, `CONTRIBUTING.md`, and `SUPPORT.md` for GitHub discovery/policy routing, not as competing full copies.
  - Remove obsolete same-topic scaffold stubs instead of maintaining parallel documentation.
  - Preserve `VERSIONS/`, `src/file_uncorrupter/legacy/`, and `docs/reports/archive/` as historical evidence.
  - Do not create deployment, governance, maintainer, citation, web-indexing, or extra legal files without evidence that they serve a current repository function.
- Consequences:
  - Root and docs indexes must link canonical paths.
  - Historical reports remain historical; current docs should not inherit their stale filesystem claims.
  - Future agents should add a conventional artifact only when it has a real current function.
- References: `docs/INDEX.md`, `AGENTS.md`, `reports/repository-baseline-2026-09-30.md`.

## Future Decisions

Add future accepted decisions using:

### YYYY-MM-DD - Decision title

- Context:
- Decision:
- Consequences:
- References:
