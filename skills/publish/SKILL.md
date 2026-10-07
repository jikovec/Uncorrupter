---
name: "publish"
description: "Force-publish the intended state by bypassing only eligible repository or deployment-process gates while preserving external platform protections."
---

# Publish

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

1. Resolve explicit force-publication intent, intended artifact/state, real target
   and applicable authority. Identify why the normal deployment path is blocked.
2. Classify the blocker by its enforcement source using the deployment contract.
   Unknown classification is unresolved, not eligible for bypass.
3. If the blocker is an eligible repository/process gate and publication authority
   covers it, use the minimum supported force path. Keep source/data safety intact.
4. If the blocker is externally enforced, preserve it even with administrator
   credentials. Prepare/repair authorized work, then report the exact requirement.
   Never disable a protection, mark a failing required check successful or substitute
   an ungoverned side channel to obtain the same prohibited effect.
5. Record failed and intentionally bypassed checks truthfully, perform publication
   only through the permitted path, and verify the resulting live identity/acceptance.

A repository-authored workflow required by branch protection is externally enforced.
A protected environment approval, required review, IAM or hosting policy is likewise
not an eligible internal gate. Force publication does not grant settings/credential
changes or privacy waivers.

Without a real target/process this CLI cannot be force-published by assumption.
`publish` is not a synonym for source push, normal deployment or package release.
Complete with target, artifact, bypass classification/authority and live evidence,
or a concrete blocked result and any completed safe preparation.
