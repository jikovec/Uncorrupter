# Scope and promotion semantics

Scope containment is not a universal override hierarchy. Authority follows the data
type: source/configuration/tests for technical truth, live Git/GitHub for work state,
accepted governance for policy, registry for configured canonical identity, and
observations for runtime state. Memory at any scope remains contextual.

| Scope | Identity and lifetime | Read visibility | Write authority | Inheritance and status | Promotion |
| --- | --- | --- | --- | --- | --- |
| global | Owner-established cross-project context; durable until revoked | Only configured global reads | Explicit/valid standing grant for global data | General defaults; cannot override authoritative repository facts | Accept only reviewed organization findings fit for global use |
| organization | Canonical organization ID; organizational lifetime | Authorized organization members/tools/scopes | Organization-governed grant | Policy constrains descendants; identity stays canonical | Organization → global needs separate destination authority |
| project | Stable project/registry ID; project lifetime across repositories | Authorized project context | Project owner/governance for appropriate records | Durable project decisions; memory summaries contextual | Project → organization only after policy/identity reconciliation |
| repository | Verified repository identity; repository lifetime across clones | Authorized checkout/remote visibility | Applicable repository grant | Source/configuration/decisions authoritative in their domain | Repository decisions → project through accepted decision references |
| agent | Established agent identity, not a claimed label; grant lifetime | Only delegated/configured readable scopes | Valid delegated rights within parent authority | Agent context cannot redefine project identity or governance | Agent findings use the task/decision promotion route |
| task | Assigned objective/work ID; accepted task lifetime | Needed authorized task context | Scoped task grant | Intent may authorize permitted actions and narrow scope | Task → project requires verified, accepted durable decision |
| session | Actual ephemeral execution identity; session lifetime | Current authorized session context | Session operations within task grant | Observations/hypotheses ephemeral; no policy authority | Session → task requires deliberate retention and task write rights |

A lower scope cannot silently rewrite higher-scope identity. Task/session memory
cannot change project IDs; agent convenience cannot create canonical registry IDs.
Current repository technical truth is not overridden by project/agent/task/session
memory. Lower scopes may narrow organization policy but cannot widen its prohibited
permissions. Repository guidance refines generic execution behavior; task/session
requests do not silently remove repository governance or safety boundaries.

Task intent may grant action authority only under the authorization model. Scope
nesting, memory, ephemeral state and identity labels never manufacture authority.

For each promotion (session → task, task → project, project → organization,
organization → global), verify all of: destination permits writes; content suits
that scope; mutation authority exists; canonical source/registry truth has been
updated first where applicable; the persistence mechanism supports the write.
Record provenance, uncertainty and canonical references. Durable technical decisions
normally enter the accepted repository decision surface before or with authorized
memory promotion. No automatic upward promotion or fabricated scope identifiers.
