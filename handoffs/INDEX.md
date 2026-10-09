# Handoffs Index

Handoffs preserve an actionable continuation boundary for future agents. Current source/tests remain authoritative.

## Current Handoffs

- [2026-09-09 - Local project orientation](2026-09-09-local-orientation.md): current project card, existing workflow reuse, host prerequisites, source/remote separation and scoped validation.
- [2026-08-05- [2026-08-05 - Stabilized multi-format recovery](2026-08-05-stabilized-multiformat-recovery.md): current 0.4.0 architecture, verification, remaining gates, and preserved local state through 2026-08-08.
- [2026-07-26 - Video/JPEG misclassification fix](2026-07-26-video-jpeg-misclassification-fix.md): concurrent declared-video/embedded-JPEG routing correction retained by stabilization.

## Related Reports

- [Stabilized multi-format implementation report](../reports/2026-08-05-stabilized-multiformat-implementation.md)
- [Pre-stabilization assessment](../reports/2026-07-26-current-state-and-roadmap-assessment.md)
- [Reports index](../reports/INDEX.md)

## Naming Convention

Use:

```text
YYYY-MM-DD-short-topic.md
```

Do not rename an existing handoff merely to change its completion date; record the continuation date inside it.

## Handoff Content

A useful handoff includes:

- task scope and authorization boundary;
- confirmed current state and evidence level;
- files/areas changed;
- exact commands and results;
- dirty/unrelated/user-owned state preserved;
- unresolved failures, skips, external dependencies, and risks;
- the safest next checks/actions;
- explicit non-goals such as no commit/push/release/deployment.

## Rules

- Never include secrets or private source content.
- Never convert local/synthetic evidence into CI/live/deployment proof.
- Never claim history that cannot be recovered from source/Git evidence.
- Link the active handoff from the root and documentation indexes.
