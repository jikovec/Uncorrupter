# Authorization

## Adopted standing grant

The owner's 2026-10-07 Repository Agent Toolkit Bootstrap request expressly adopts
this contract (recorded in [decisions](../../docs/decisions.md)). For this verified
user-owned `jikovec/Uncorrupter` repository, ordinary repository workflow necessary
to complete requested work is standing-authorized:

- branches/worktrees and scoped repository edits;
- fetch/pull, non-destructive integration by rebase or merge;
- coherent commits, normal push, PR creation/update;
- task-related check/review remediation and ordinary Issue/Project work maintenance;
- merge after applicable requirements pass and completed task-branch cleanup.

This replaces older generic action-by-action consent language for ordinary source
work. It is not inferred from repository ownership alone: the adoption supplies
the grant; verified ownership establishes its applicable domain. Revalidate policy,
current scope and relevant grants at start/resume and before consequential effects.

## Boundaries

A narrow/local-only task narrows the grant. It does not authorize adjacent work,
merging someone else's PR, releasing packages, creating tags/releases, deployment,
force publication, system activation, settings/billing changes, credentials work,
data migration or cross-repository changes without coverage for that effect.
Inspect indirect push/merge triggers before delivery. Release/deployment/publication
requests use the [deployment contract](deployment.md); never silently elevate push.

Dropie, VaultGuard and external repositories retain their own governing rules.
Unknown ownership must be resolved before relying on an ownership-based grant.
Scope, memory, labels, tools, credentials and administrator capability cannot create
rights. Delegate only covered work and retain responsibility for integration.

External platform protections remain authoritative, including required checks and
reviews, branch/ruleset protection, protected environments, provider policy and IAM.
Never administratively bypass them. Governance changes need explicit authoring
rights and valid adoption before or atomically with governed work; a proposed edit
cannot authorize itself. Destructive actions and protected-history rewrites require
express authority and current-state safeguards.

Reuse valid authority across retries without repeated confirmation. If a needed
right is absent, finish independent preparation, identify the exact blocked effect
and governing source, and request only the concrete missing authorization.
