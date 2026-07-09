# Root Reports Index

Tags: #agent/report #repo/index

This directory stores root-level workflow reports, validation summaries, implementation evidence, and Codex handoff-adjacent notes. Curated documentation reports and historical research live under [docs/reports](../docs/reports/).

## Current Reports

- [Memory workflow validation - 2026-07-07](2026-07-07-memory-workflow-validation.md) - validated the repo-root memory workflow against current CLI, docs, and tests.
- [Multi-repo finalization - 2026-07-07](multi-repo-finalization-2026-07-07.md) - preserved the current documentation package and noted release archive review risk.
- [Obsidian and agent indexing plan - 2026-07-09](obsidian-agent-indexing-plan.md) - planned the complete local Obsidian and future-agent orientation system.
- [Obsidian and agent indexing implementation - 2026-07-09](obsidian-agent-indexing-implementation-2026-07-09.md) - implementation report for the docs/indexing system.
- [Obsidian and agent indexing audit - 2026-07-09](obsidian-agent-indexing-audit-2026-07-09.md) - verification and hardening pass for the docs/indexing system.

## Report Guidelines

- Use root `reports/` for workflow evidence, validation findings, implementation reports, and memory-system reviews.
- Use [docs/reports](../docs/reports/) for curated documentation reports and historical research.
- Keep reports factual and source-backed.
- Record exact commands run and exact blockers.
- Do not include secrets, tokens, account IDs, private URLs, private media paths, or private machine-specific paths.
- Do not claim manual UI, Obsidian, FFmpeg, deployment, or pytest validation unless it was actually run and observed.

## Maintenance

When adding a report:

- Add it to this index.
- Link it from [00_Index.md](../00_Index.md) if it is useful for future orientation.
- Update [docs/current-state.md](../docs/current-state.md) if it changes the current state or known risks.
- Add a handoff under [handoffs](../handoffs/) only when there is specific follow-up work for a future agent.
