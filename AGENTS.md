<!-- codex-memory-scaffold:agents-workflow -->
## Codex Project Memory Workflow

- Before meaningful work, read 00_Index.md, docs/current-state.md, and docs/decisions.md.
- Inspect relevant files under reports/ and handoffs/ before editing behavior touched by prior work.
- Preserve existing behavior unless the user explicitly asks for a behavior change.
- Avoid secrets, credentials, private keys, .env files, generated dependency folders, build outputs, and release archives.
- Prefer minimal, reviewable changes that match the existing project structure.
- Run the relevant checks listed in docs/commands.md or docs/testing.md when possible.
- After meaningful changes, update docs/current-state.md or add a dated handoff note under handoffs/.
<!-- /codex-memory-scaffold:agents-workflow -->

## Documentation And Agent Orientation

- Future agents should start with `00_Index.md`, `docs/AGENT-INDEX.md`, `docs/SOURCE-MAP.md`, and `docs/CONNECTIONS.md` before changing documentation or behavior.
- Treat source, `pyproject.toml`, and tests as higher-priority truth than historical reports or release archives.
- Keep Obsidian integration local-first and plaintext; `.obsidian/` remains ignored and must not be used for cloud, account, sync, or encryption setup.
- Keep `.agents/` and `.specify/` local-only unless a future explicit decision changes that.
- Update `docs/agent-index.json` whenever paths, commands, tags, safety rules, or known risks change.
