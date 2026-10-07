<!-- codex-memory-scaffold:decisions -->
# Decisions

## Active Decisions
- No project decisions were invented during scaffolding.

## Decision Log
Add future decisions here using this structure:

### YYYY-MM-DD - Decision Title
- Context:
- Decision:
- Consequences:
- References:

## Linked Decision Records
- Add links to ADRs or existing decision files when they are confirmed current.

## Documentation Indexing Notes
- The current agent and Obsidian orientation system uses existing docs rather than creating duplicate uppercase docs such as `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `docs/SECURITY.md`, or `docs/DECISIONS.md`.
- `docs/agent-index.json` is the canonical machine-readable agent index.
- `.agents/index.json` is omitted because `.agents/` is local-only ignored Spec Kit scaffolding in this repo.
- These notes document the current documentation structure; they are not product architecture decisions.

## 2026-10-07 - Portable repository agent toolkit adoption

- Context: The owner explicitly requested the Repository Agent Toolkit Bootstrap,
  including policy authoring and ordinary source delivery through merge. Existing
  local deploy-as-push guidance and generic action-by-action consent wording conflicted
  with the requested workflow semantics.
- Decision: Adopt `AGENTS.md`, `.agent/project.yaml`, `.agent/contracts/` and `skills/`
  as the canonical portable layer. Adopt the scoped standing source-workflow grant
  in `.agent/contracts/authorization.md`; narrower task scope and external protections
  remain binding. Release/deploy/publish remain distinct from source delivery.
- Discovery: Share `.codex/skills/` and `.claude/skills/` pointers only. Codex 0.159.2
  loads `.codex/skills/` natively; publishing a second `.agents/skills/` adapter set
  produced duplicate entries in a real discovery probe. Keep `.agents/` and `.specify/`
  local-only. Reverify discovery when changing provider versions or paths.
- Migration: `deploy` now means governed live deployment; `push` owns source delivery.
  `docs/agent-workflow.md` becomes a compatibility index. Existing Spec Kit scaffolding,
  manual environment actions and unrelated uncommitted product work are preserved.
- Identity: Use repository-qualified `github:jikovec/Uncorrupter` as the stable portable
  fallback. No verified canonical Mind-Seed binding was found; keep integration disabled
  and reconcile before enrollment. Do not create registry or memory records.
- Consequences: Provider files do not fork policy. Durable decisions remain repository
  first. Runtime behavior, package metadata and release artifacts are unchanged.
- References: [toolkit](../.agent/README.md), [authorization](../.agent/contracts/authorization.md),
  [provider migration](../.agent/workflows/provider-discovery.md).
