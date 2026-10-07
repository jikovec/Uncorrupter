---
name: "push"
description: "Finalize completed local work through the repository's normal commit, push, pull-request, check, and merge workflow."
---

# Push

## Shared contracts

- [authorization](../../.agent/contracts/authorization.md)
- [verification](../../.agent/contracts/verification.md)
- [git-github](../../.agent/contracts/git-github.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Inspect current status, branch, upstream and task-owned diffs. Fetch current
   upstream and relevant PR/check state; identify overlapping work and triggers.
2. Preserve unrelated work and stage only exact reviewed task paths. Run applicable
   checks and create coherent commits if needed; never manufacture an empty commit.
3. Push normally and verify the remote ref matches the intended head. Resolve a
   non-fast-forward through the Git contract rather than default force-pushing.
4. Reuse/create the task PR and inspect current exact-head checks/reviews. Repair
   only task-caused failures, rerun affected checks and refresh head evidence.
5. Complete permitted merge after applicable requirements pass, then fetch and
   verify the resulting default branch. Leave a dirty original checkout intact.

Respect a narrower task endpoint such as local-only or push-only. Ordinary scoped
source delivery is covered by the adopted authorization contract, so do not ask
again after each step. Release tags, package uploads and deployment are not inherent
parts of push. Reinspect indirect trigger effects before remote mutation.

If CI is not configured, disclose that no remote test execution was established;
do not fabricate green checks or create CI simply to satisfy an old local deploy
command. Existing enforced requirements always remain binding.

Complete with commit/remote/PR/merge evidence, check status and preserved-work notes.
Use `release` for release state and `deploy` for a concrete live target.
