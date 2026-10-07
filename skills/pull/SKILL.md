---
name: "pull"
description: "Safely synchronize local repository state with upstream while preserving unrelated work and reconciling conflicts according to repository conventions."
---

# Pull

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [authorization](../../.agent/contracts/authorization.md)
- [git-github](../../.agent/contracts/git-github.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Inspect status, staged/untracked work, HEAD, branch/upstream and remotes before
   changing any checkout. Fetch the canonical remote and resolve intended upstream.
2. Compare ancestry and task scope. Fast-forward a clean branch when possible;
   otherwise choose the repository-appropriate merge/rebase strategy from the Git
   contract. Preserve shared history and concurrent work.
3. When the checkout is dirty or changes overlap, use isolation for independent
   work; do not overwrite local files, stash, reset or clean as an automatic solution.
   Surface the exact conflicting paths and retain their evidence.
4. Resolve understood task-scoped conflicts, then run the checks affected by the
   integration. Stop the ambiguous part and complete independent preparation.
5. Verify resulting local branch/HEAD, upstream relation and status, including
   preservation of unrelated changes.

Fetching a remote ref is not checkout synchronization. A dirty checkout left intact
must be reported as preserved and unsynchronized, not updated. Do not create PRs,
release artifacts, memory records or production effects merely to synchronize.

A question about upstream divergence without an update request routes to
`investigate`. Complete with before/after identity, actual integration method,
verification and precise remaining conflicts or prerequisites.
