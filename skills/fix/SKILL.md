---
name: "fix"
description: "Diagnose and repair a known defect, failed check, incomplete prior change, review finding, or inconsistency between authoritative project states."
---

# Fix

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [authorization](../../.agent/contracts/authorization.md)
- [verification](../../.agent/contracts/verification.md)
- [git-github](../../.agent/contracts/git-github.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Reproduce or establish the known defect against the actual target state. Inspect
   relevant source, tests, reports and overlapping work; preserve unrelated changes.
2. Trace cause before editing. Add a focused regression for consequential behavior;
   for metadata/docs use the relevant structural and consistency checks.
3. Implement the smallest complete causal repair. Do not hide failures with retries,
   delays, weakened assertions, blanket exception suppression or unsupported claims.
4. Rerun affected checks and the proportional native verification set. Update stale
   affected guidance and machine-index entries.
5. Review and deliver through the authorized repository lifecycle, remediating only
   task-caused CI/review failures. Report unrelated defects separately.

`reconcile` is this workflow with state-reconciliation intent. Distinguish source,
documentation, Git, GitHub, deployment/runtime, registry, memory and prior handoffs;
resolve each discrepancy using its authoritative source. Avoid duplicate work items.
Read memory/scopes only when persistent state or identity is involved. Fixing code
does not implicitly grant a memory write or deployment.

For recovery defects follow the shared recovery-evidence process. Complete with the
causal correction, regression/verification result, exact delivered state and any
remaining blocker. New substantial behavior without a defect routes to `build`.
