---
name: "review"
description: "Review a change, branch, pull request, or implementation for material correctness, regression, architecture, security, and maintainability issues."
---

# Review

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [verification](../../.agent/contracts/verification.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Pin the review target and comparison base. Inspect relevant instructions, intent,
   changed code and callers/tests; preserve concurrent and unrelated work.
2. Evaluate correctness and requested behavior first, then regressions/contracts,
   architecture, security, tests, maintainability and relevant performance or
   accessibility. Style matters only when material to the change.
3. Reproduce suspected defects with bounded checks when possible. Trace concrete
   triggers and consequences; do not report speculation as established failure.
4. For each actionable finding give severity, exact location, causal explanation,
   affected behavior and a useful correction direction. Avoid cosmetic noise.
5. Report checks performed, material gaps and residual risk, including when no
   actionable issue was found. A clean review is not proof of all runtime behavior.

Read Git/GitHub when reviewing branches/PRs. For recovery changes consult the shared
recovery-evidence workflow. A review request alone does not authorize repairs,
remote review submission, approval, merge or publication. If submission is requested,
use the authorized channel and disclose only appropriate source evidence.

Complete with prioritized evidence-backed findings and the target identity. To
repair an accepted finding use `fix`; to test a specific completion claim use `verify`.
