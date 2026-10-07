---
name: "uncorrupter-workflow"
description: "Validate UNCorrupter recovery changes and evidence using synthetic damaged-file fixtures, decoder boundaries, provenance and fidelity checks."
---

# Uncorrupter Workflow

## Shared contracts

- [core](../../../.agent/contracts/core.md)
- [verification](../../../.agent/contracts/verification.md)
- [handoff](../../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../../.agent/project.yaml) and the relevant existing
[commands](../../../docs/commands.md). For recovery behavior use
[recovery evidence](../../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

Use this skill alongside the selected generic workflow for recovery behavior,
capability claims, source/output safety or persisted evidence. It supplies the
project process, not a separate authorization or delivery policy.

1. Read [recovery evidence](../../../.agent/workflows/recovery-evidence.md) and the
   checkout's actual source, manifest, command docs and relevant tests.
2. Identify the changed recovery path and its evidence claim. Connect inputs,
   classification, candidate/goal behavior, validation, outputs and report persistence.
3. Exercise affected paths with synthetic fixtures and disposable outputs. Verify
   source preservation, output separation and relevant budgets/tool failure modes.
4. Distinguish structural decodability, recovered content, derivative previews,
   unavailable optional tools and unknown semantic fidelity.
5. Update the affected docs/index and report results under the parent task endpoint.

Existing shorthand requests retain routing: inspect → investigate; implement →
build/fix; verify → verify; prepare delivery/finish → push under the task scope.
Load only the selected generic workflow; do not run every workflow in sequence.

Do not assume capability commands, handler registries or newer test files exist
merely because another dirty checkout has them. Source and tests in the target
checkout govern the actual commands. Toolkit-only metadata edits use toolkit
validation and do not require recovery execution.

Complete with the affected format/operation, input/output invariants exercised,
exact checks/tool availability and honest fidelity limits. No real private corpus
is uploaded and no release/deployment is inferred from a recovery test.
