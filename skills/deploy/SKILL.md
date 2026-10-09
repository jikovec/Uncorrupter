---
name: "deploy"
description: "Deploy the intended repository state through its normal governed deployment process and verify the resulting live state."
---

# Deploy

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [authorization](../../.agent/contracts/authorization.md)
- [verification](../../.agent/contracts/verification.md)
- [deployment](../../.agent/contracts/deployment.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Identify the intended immutable source/artifact, actual deployment target,
   existing deployment process and action authority. Inspect real configuration
   and provider requirements; do not invent a target from tool availability.
2. Determine normal checks, environment approvals, migration/rollback needs and
   acceptance observations for that target. Follow every applicable gate.
3. Prepare and validate the deployable state. Use the governed procedure to deploy
   only when prerequisites and authority cover the effect.
4. Read back deployment identity and perform the configured health/acceptance checks.
   Distinguish command success, rollout completion and observed live behavior.
5. Repair task-caused failures within scope or follow the real rollback process
   when authorized. Report partial effects and unresolved requirements precisely.

The old local deploy-as-branch-push meaning is retired. Source delivery routes to
`push`. This CLI currently has no maintained hosted deployment configuration;
requesting deploy without a concrete target cannot be fulfilled by pushing a branch.
Prepare what is supported and identify the missing target/procedure.

Never silently switch to `publish` or bypass external protections. A failed normal
process remains failed until corrected. Complete with source/artifact identity,
target, deployment result and observed acceptance, or the exact prerequisite that
prevented the live effect.
