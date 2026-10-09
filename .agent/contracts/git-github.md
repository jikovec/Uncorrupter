# Git and GitHub workflow

Read [authorization](authorization.md) before writes. Use this lifecycle for scoped
source delivery; the task can end earlier when it explicitly requests local work.

1. Capture status (including staged/untracked paths), HEAD, branch/upstream, remotes
   and relevant diffs. Fetch the canonical remote with prune. Resolve current default
   branch, open related Issues/PRs/Projects, checks and relevant tags/releases.
2. Preserve unrelated work. Prefer an isolated worktree based on current upstream
   for delivery when a dirty checkout contains another candidate. Do not incorporate
   that candidate or another PR merely because files overlap. Use `codex/<task>` for
   a new branch unless an existing applicable convention is more specific.
3. Review upstream divergence. Fast-forward a clean local branch where possible;
   rebase unpublished task commits or merge upstream when shared history should stay
   stable. Never use reset/clean/stash as an automatic synchronization strategy.
   Resolve only understood in-scope conflicts; retain evidence for ambiguous overlap.
4. Verify the change using current source and native checks. Update affected guidance
   and a dated handoff. Inspect triggers for release/deployment side effects before
   push or merge; stop the uncovered effect, not independent preparation.
5. Stage an explicit allowlist of task-owned paths, inspect staged diff and whitespace,
   then commit cohesively. Use a concise imperative subject; follow any established
   convention. Never include private recovery inputs or generated run evidence.
6. Push normally and verify the remote head SHA. Reuse an existing task PR or create
   one against the intended base. Respect the configured draft default; mark ready
   only after scoped implementation/review/verification is complete. Explain behavior,
   scope and checks without copying private conversation material into GitHub.
7. Read current required checks, reviews and merge state for that exact head. Repair
   in-scope CI/review failures; do not weaken gates or accept a skipped test as a pass.
   No configured CI is a disclosed evidence limitation, not a fabricated check.
   Search for duplicate work items before creating any; do not close adjacent issues.
8. Revalidate head/base and applicable governance. Merge using a repository-supported
   method only after requirements pass. Never use administrative bypass. Use an
   expected-head guard where supported; re-review when concurrent changes invalidate
   evidence. Do not merge another open PR as incidental cleanup.
9. Fetch and verify the resulting default-branch commit/tree includes the reviewed
   change. Inspect post-merge checks when configured. Safely synchronize only clean
   checkouts. Leave a dirty original checkout intact and identify the verified worktree.
   Clean up only task-owned branches/worktrees with no unpreserved work when useful.

Normal non-force push is the default. History rewrite needs express valid coverage,
fresh remote evidence and an exact lease; protected-history rewrite is never inferred
from ordinary workflow authority. Enforced protections are not eligible bypass gates.
