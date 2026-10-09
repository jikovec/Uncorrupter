# Root Reports Index

Root reports capture dated implementation, audit, and verification evidence. They do not override current source/tests and do not by themselves prove a release, deployment, or live behavior.

## Current Reports

- [2026-08-05 - Stabilized multi-format recovery implementation](2026-08-05-stabilized-multiformat-implementation.md): implementation scope, commands, checks, preserved boundaries, and remaining gates through 2026-08-08.
- [2026-07-26 - Current state and roadmap assessment](2026-07-26-current-state-and-roadmap-assessment.md): pre-stabilization evidence and gaps; superseded for current behavior but retained as baseline.
- [2026-07-07 - Memory workflow validation](2026-07-07-memory-workflow-validation.md): documentation/memory scaffolding validation.
- [Obsidian agent indexing plan](obsidian-agent-indexing-plan.md)
- [Obsidian agent indexing implementation](obsidian-agent-indexing-implementation-2026-07-09.md)
- [Obsidian agent indexing audit](obsidian-agent-indexing-audit-2026-07-09.md)

## Related Handoffs

- [2026-08-05 - Stabilized multi-format recovery](../handoffs/2026-08-05-stabilized-multiformat-recovery.md)
- [2026-07-26 - Video/JPEG misclassification fix](../handoffs/2026-07-26-video-jpeg-misclassification-fix.md)
- [Handoffs index](../handoffs/INDEX.md)

## Report Requirements

A substantive report should record:

- scope and authorization boundary;
- initial Git/worktree and pre-existing-change boundary;
- inspected/implemented files or grouped areas;
- exact relevant commands with secrets removed;
- check results, failures, skips, and environment;
- implemented/tested/live/deployed labels kept distinct;
- unverified areas and remaining risks;
- no remote/release/deployment claim unless directly proven.

## Maintenance

Index new root reports here and link the active one from `00_Index.md`, `docs/current-state.md`, `docs/AGENT-INDEX.md`, and the corresponding handoff.
