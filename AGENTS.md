<!-- codex-memory-scaffold:agents-workflow -->
# Agent Workflow

Before meaningful work, read `00_Index.md`, `docs/current-state.md`, `docs/decisions.md`, and the relevant current documentation under `docs/`.

## Authority

1. Current source, tests, package/build configuration, and live repository state.
2. Current canonical documentation.
3. Reports and handoffs.
4. Historical research and release archives.

When sources conflict, verify the current default branch and record the conflict instead of silently choosing stale documentation.

## Scope And Safety

- Preserve established project terminology, architecture, and behavior unless the task explicitly changes them.
- Treat input media as hostile. Preserve original evidence; use separate output/database/workspace locations.
- Do not add secrets, credentials, private paths, private media details, account identifiers, or `.env` contents.
- Preserve unrelated dirty and untracked work. Do not reset, stash, discard, or overwrite it.
- Keep `.obsidian/`, `.agents/`, and `.specify/` local-only unless an explicit repository decision changes that.
- Historical material under `VERSIONS/`, `docs/reports/archive/`, and `src/file_uncorrupter/legacy/` is evidence, not current implementation authority.

## Work Management And Delivery

For material repository work, use the repository work ledger and normal flow:

`Issue / work object -> branch -> implementation -> verification -> pull request`

Do not merge, tag, release, publish, deploy, or change repository settings unless the current task explicitly authorizes that effect.

## Verification

Use only commands supported by current repository tooling. Start with:

- `git status --short --branch`
- `git diff --check`
- `python -m json.tool docs/agent-index.json` when the index changes
- `python -m pytest` when runtime, tests, package metadata, or behavior-facing documentation requires it

Never report an unavailable or unrun check as passing.

## Documentation Obligations

- `docs/INDEX.md` is the current documentation hub.
- `docs/architecture/ARCHITECTURE.md`, `docs/setup/DEVELOPMENT.md`, `docs/testing/VERIFICATION.md`, and `docs/security/SECURITY.md` are canonical for their subjects.
- Update `docs/current-state.md` when repository state or documented operational facts change.
- Update `docs/SOURCE-MAP.md` and `docs/CONNECTIONS.md` when source/test/document relationships change.
- Update `docs/agent-index.json` when agent-facing paths, commands, safety rules, or known risks change.
- Add durable validation/implementation evidence under `reports/` when repository policy calls for it.
<!-- /codex-memory-scaffold:agents-workflow -->
