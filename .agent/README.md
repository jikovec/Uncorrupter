# Repository agent toolkit

Start at [AGENTS.md](../AGENTS.md). Stable identity is in [project.yaml](project.yaml),
written in JSON notation, a YAML 1.2 subset that the Python standard library can
validate without another dependency. It contains no branch, commit or test status.

| Concern | Canonical surface |
| --- | --- |
| Evidence, architecture, scope discipline | [core](contracts/core.md) |
| Standing mutation rights | [authorization](contracts/authorization.md) |
| Checks and evidence categories | [verification](contracts/verification.md) |
| Source synchronization and delivery | [Git/GitHub](contracts/git-github.md) |
| Release, deployment and force publication | [deployment](contracts/deployment.md) |
| Completion evidence | [handoff](contracts/handoff.md) |
| Persistent context and promotion | [memory](contracts/memory.md), [scopes](contracts/scopes.md) |
| Reusable recovery process | [workflows](workflows/README.md) |
| External services and credentials boundary | [integrations](integrations/README.md) |
| Deterministic validation | [hooks](hooks/README.md) |
| Skill selection examples | [routing evaluations](evals/skill-routing.md) |

Canonical workflows: [build](../skills/build/SKILL.md),
[investigate](../skills/investigate/SKILL.md), [research](../skills/research/SKILL.md),
[verify](../skills/verify/SKILL.md), [review](../skills/review/SKILL.md),
[fix](../skills/fix/SKILL.md), [release](../skills/release/SKILL.md),
[deploy](../skills/deploy/SKILL.md), [publish](../skills/publish/SKILL.md),
[push](../skills/push/SKILL.md), [pull](../skills/pull/SKILL.md), and
[uncorrupter-workflow](../skills/project/uncorrupter-workflow/SKILL.md).
Aliases are intent mappings, not duplicate implementations: develop → build;
reconcile → fix.

Codex 0.159.2 natively discovers the checked-in `.codex/skills/` adapters.
Only one adapter set is shared to avoid duplicate entries. Claude uses `.claude/skills/` and
`CLAUDE.md` imports `AGENTS.md`. See [provider discovery](workflows/provider-discovery.md).
The old local deploy-as-push workflow is retired in toolkit-enabled checkouts.
Existing Spec Kit skills and `.specify/` remain optional local tools, not a
parallel authorization source. No provider hook or external service is activated.

Mind-Seed integration is disabled until a canonical binding is established.
No registry ID, memory scope, organization or cross-project relationship is guessed.
Do not infer enrollment from a workspace's filesystem location or a visible connector.
Reconcile existing bindings before enabling that layer; use the memory/scope contracts.
