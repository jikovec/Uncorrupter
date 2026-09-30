# Future-Agent Orientation

Tags: #agent/orientation #repo/index #uncorrupter/recovery

## Start Here

Read in this order before meaningful work:

1. [AGENTS.md](../AGENTS.md)
2. [Root index](../00_Index.md)
3. [Current state](current-state.md)
4. [Decision log](decisions.md)
5. [Documentation index](INDEX.md)
6. [Project overview](PROJECT-OVERVIEW.md)
7. [Source map](SOURCE-MAP.md)
8. [Connection map](CONNECTIONS.md)
9. [Developer setup](setup/DEVELOPMENT.md)
10. [Testing and verification](testing/VERIFICATION.md)
11. [Security model](security/SECURITY.md)

For durable evidence and deferred work:

- [Root reports index](../reports/INDEX.md)
- [Root handoffs index](../handoffs/INDEX.md)
- [Curated documentation reports](reports/INDEX.md)

Machine-readable orientation: [agent-index.json](agent-index.json).

## Source Of Truth

Use this order when information conflicts:

1. Current source, tests, package/build configuration, and live repository state.
2. Current canonical documentation.
3. Root reports and handoffs.
4. Curated historical documentation.
5. Historical release artifacts.
6. Explicitly marked inference.

Do not treat project-memory notes, old reports, or archives as proof of current implementation.

## Product Boundary

Current public interface: the `file-uncorrupter` CLI with `scan`, `classify`, `recover`, `benchmark`, and `report`.

The current repository defines no HTTP API, hosted service, authentication layer, telemetry upload, deployment workflow, or remote service integration.

## Work And Delivery Rules

- Inspect the live GitHub issue/PR state before material work.
- Preserve unrelated dirty/untracked local changes.
- Use `Issue -> branch -> implementation -> verification -> pull request` for material changes.
- Do not merge, deploy, publish, release, tag, or change repository settings without explicit authorization.
- Keep changes bounded to the current work object.

## Security And Privacy Rules

- Treat input media as hostile.
- Keep source evidence separate from outputs, databases, reports, raw candidates, and workspace state.
- Do not add secrets, credentials, private paths, private media details, account IDs, private URLs, or `.env` contents.
- Keep `.obsidian/`, `.agents/`, and `.specify/` local-only unless an explicit repository decision changes that.

## Update Obligations

After meaningful repository changes, update only the affected canonical surfaces:

- [current-state.md](current-state.md) for current repository facts.
- [SOURCE-MAP.md](SOURCE-MAP.md) for source/test responsibilities.
- [CONNECTIONS.md](CONNECTIONS.md) for documentation/source/test/report relationships.
- [agent-index.json](agent-index.json) for machine-readable agent paths, commands, rules, and risks.
- [reports/](../reports/) for durable validation/implementation evidence when required.
- [handoffs/](../handoffs/) for specific deferred work.

## Common Verification

Use the smallest relevant check set:

```text
git status --short --branch
git diff --check
python -m json.tool docs/agent-index.json
python -m pytest
```

`python -m pytest` requires pytest to be installed in the active environment. Record unavailable checks exactly; do not convert unavailable into passed.

## Historical Boundaries

- `VERSIONS/` is historical release evidence.
- `src/file_uncorrupter/legacy/` is historical source evidence.
- `docs/reports/archive/` is historical research evidence.
- Historical reports can contain superseded claims; preserve their historical accuracy instead of rewriting them as current docs.
