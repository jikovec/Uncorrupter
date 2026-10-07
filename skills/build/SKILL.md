---
name: "build"
description: "Implement substantial repository changes and carry them through relevant verification and normal repository completion workflow."
---

# Build

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

1. Establish requested behavior, scope and final endpoint from the task and current
   source. Read applicable instructions and inspect status/upstream/overlapping work.
2. Use an isolated branch/worktree where needed. Keep the accepted architecture and
   dependencies unless the change requires a justified adjustment.
3. Implement the complete scoped outcome, including error handling and appropriate
   tests. For recovery behavior use the shared recovery-evidence workflow.
4. Verify proportionately, repair task-caused failures and rerun affected checks.
   Update stale canonical documentation and the machine index when relevant.
5. Review the task delta and complete the authorized Git/GitHub lifecycle. Keep
   task-related CI/review remediation within scope; preserve unrelated work.

A known defect belongs to `fix`; external evidence needed for an implementation can
use `research` without turning a research-only request into code changes. `develop`
is an alias for this workflow. Do not release, deploy or publish automatically.

Complete when requested behavior and relevant checks are accounted for and the
requested endpoint is reached. Report exact change identity, checks, delivery state
and unresolved prerequisites; local green tests do not establish live acceptance.
