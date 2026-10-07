---
name: "investigate"
description: "Inspect repository, runtime, or work state to establish current behaviour, root cause, or required work without changing implementation by default."
---

# Investigate

## Shared contracts

- [core](../../.agent/contracts/core.md)
- [handoff](../../.agent/contracts/handoff.md)
## Project context

Read [project metadata](../../.agent/project.yaml) and the relevant existing
[commands](../../docs/commands.md). For recovery behavior use
[recovery evidence](../../.agent/workflows/recovery-evidence.md).

## Workflow and completion

1. Frame the question and collect current source/configuration, focused tests, logs
   or live read-only observations. Inspect only what can resolve the uncertainty.
2. Trace the behavior or discrepancy to its owning path. Separate committed source,
   dirty candidates, runtime observations and historical claims.
3. Test hypotheses with bounded, non-destructive diagnostics and synthetic fixtures
   where appropriate. Do not inspect private damaged files without that scope.
4. Label findings observed, supported, inferred or unknown. Identify causal evidence,
   impact and the smallest next action; explain remaining uncertainty.

Read the Git contract only for branch/work-state investigation. Read memory/scope
contracts only for persistent context, registry or cross-project questions.
This workflow defaults to read-only: do not quietly repair the implementation,
create work items, persist memory or advance delivery. A later repair request routes
to `fix`; external standards/API comparison routes to `research`.

Complete with an evidence-backed answer, reproducible diagnostic steps when useful,
and clearly bounded next work. An unresolved hypothesis is not a confirmed defect.
