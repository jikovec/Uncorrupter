---
name: "verify"
description: "Independently verify claimed repository, branch, PR, release, deployment, or live state using current evidence."
---

# Verify

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [verification](../../.agent/contracts/verification.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Identify the claim, acceptance criterion and exact object: checkout/commit, PR,
   artifact, release, deployment or observed runtime. Prior agent summaries are
   leads, not proof.
2. Read current source/configuration and retrieve the relevant live state. Select
   the smallest native checks that can establish or refute the claim.
3. Execute those checks safely and retain attributable results. Correlate remote
   checks with the exact head and artifact/live observations with deployed identity.
4. Classify each result using the verification contract. Separate missing evidence
   from a demonstrated failure; do not weaken a criterion to obtain a pass.
5. Report a bounded verdict with supporting evidence and precise limitations.

Load Git/GitHub, deployment or memory/scope contracts only when those states are
under verification. For recovery claims use the shared recovery-evidence process.
Do not repair implementation or mutate remote state under a verification-only task.
If the user also authorized repairs, explicitly route that work through `fix` and
rerun affected verification afterward.

Complete with an independently supported verdict for each material claim. A merge
proves source integration; a build proves buildability; neither proves deployment
or fidelity of a real recovered document.
