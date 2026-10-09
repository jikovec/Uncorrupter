---
name: "release"
description: "Prepare and complete the repository's normal release workflow, including versioning, notes, tags, artifacts, or release records where applicable."
---

# Release

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [authorization](../../.agent/contracts/authorization.md)
- [verification](../../.agent/contracts/verification.md)
- [git-github](../../.agent/contracts/git-github.md)
- [deployment](../../.agent/contracts/deployment.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Resolve release scope, intended source, target/version and action authority.
   Inspect actual manifests, version surfaces, changelog, tags, release records and
   configured build/release workflows; never infer mechanics from archive filenames.
2. Determine prerequisites: consistent versions, reviewed notes, relevant checks,
   artifact provenance and intended distribution. Record missing release procedure
   or destination as a prerequisite instead of creating one silently.
3. Prepare the scoped version/notes/artifacts using established commands. Preserve
   historical archives and exclude private samples, databases and run reports.
4. Verify artifacts against the intended source and applicable checks. Complete
   authorized source delivery before creating release state when the process requires it.
5. Create only authorized tags/release records/uploads using the established path;
   verify exact tag, source and artifact identity after the effect.

This local CLI has no established automated release path in the tracked baseline.
Do not infer PyPI publication, GitHub binary distribution, Pages or live deployment
from package build capability. Missing target/procedure needs a concrete owner
choice; finish independently authorized preparation first.

Complete with version/tag/artifact/release links and actual publication state.
A prepared release or source merge does not establish deployed live acceptance.
