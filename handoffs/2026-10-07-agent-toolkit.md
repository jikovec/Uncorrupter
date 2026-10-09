# Repository agent toolkit — 2026-10-07

## Scope and baseline

The owner requested adoption and delivery of the portable Repository Agent Toolkit
Bootstrap. Implementation began from fetched `origin/main` at
`70fd1188d3a0ff9ea08e526924eada70532cb582` on an isolated
`codex/repository-agent-toolkit` branch. Repository identity is public
`jikovec/Uncorrupter`, personal owner `jikovec`, default branch `main`, organization
unset. Stable portable project identity is `github:jikovec/Uncorrupter`.

The original checkout contains a substantial uncommitted recovery candidate and
local documentation/skill/environment setup. It is preserved separately; no product
source, tests, package metadata, license or release archive enters this toolkit change.
Open PR #11 and Issues #7/#10 cover a separate repository documentation baseline;
this task neither incorporates nor merges that work. Future integration must preserve
this toolkit's adopted contracts when resolving overlapping documentation.

## Resulting infrastructure

- `AGENTS.md` routes to `.agent/project.yaml`, eight shared contracts, eleven baseline
  skills and the recovery-specific `uncorrupter-workflow` skill.
- Recovery verification and provider discovery are shared workflows. GitHub is the
  configured source/work-management integration. No speculative cloud integration,
  account setup, external registry record or deployment service was created.
- Codex and Claude adapters are thin pointers; `CLAUDE.md` imports `AGENTS.md`.
  The former local deploy-as-push meaning is retired in toolkit-enabled checkouts.
  `push` owns source delivery; `release`, `deploy` and `publish` have distinct semantics.
- `docs/agent-workflow.md` is a compatibility index; navigation, source/connection
  maps, current-state note and machine-readable index route to the canonical layer.
- A manually invoked dependency-free hook checks structure, metadata, links, routing
  coverage and adapter parity. No Git/provider hook, CI or background job is installed.
- The owner's explicit adoption is in `docs/decisions.md`. It grants ordinary scoped
  repository workflow through merge; release/deployment effects and external platform
  protections remain separately governed. No authority is derived from credentials.

## Identity and memory limitations

No project-local Mind-Seed metadata, registry identity, designated project enrollment
or persistent scope binding was established. The available MemPalace read probe
returned `UNAVAILABLE` with HTTP 404. External registry reconciliation could not be
completed; absence of a registry entry is not claimed. Mind-Seed remains disabled
with a null binding. No organization, registry ID, scope ID or relationship was
invented. No memory or registry mutation occurred. Contracts define scope semantics,
repository-first decisions and explicit promotion/write authority for future use.

## Verification

Passed on Python 3.12.14:

- Toolkit validator: project metadata in YAML-compatible JSON notation; twelve
  canonical frontmatters; eight contracts; two native adapter sets; local links;
  three positive and two negative routing examples per skill.
- Seven regression scenarios reject malformed metadata, unverified memory activation,
  provider policy forks, missing canonical skills, duplicate frontmatter, duplicate
  legacy discovery and links escaping the repository.
- Machine-index JSON parse, changed Markdown link checks, patch whitespace review
  and task-path inspection. Required `build` skill paths are explicitly unignored.
- Independent read-only semantic evaluation matched all 60 routing cases and four
  baseline scenarios. This is a guidance review, not a blind model benchmark or
  execution proof of the described workflows.
- Codex CLI 0.159.2 native `skills/list` with forced reload discovers all twelve
  repository skills once, enabled, without loader errors through `.codex/skills/`.
  The first probe found that adding `.agents/skills/` too produced duplicate entries;
  the redundant set was removed and native discovery rerun successfully.

- Claude Code 2.1.282 native initialization exposes all twelve toolkit skills; the
  read-only no-tool discovery session completed with exit 0 and no error events.

Recovery runtime tests/build: not required for this guidance-only change; source,
package configuration and runtime tests are unchanged. The host has Python but lacks
pytest and Pillow in that environment; historical Windows test results were not
reused as current proof. The generic skill-creator validator needs unavailable PyYAML;
this toolkit instead validates its explicitly constrained YAML-compatible notation
with the standard library and native Codex loading.

Remote CI: the current default branch has no Actions workflows or configured branch
protection/rulesets; no exact-head remote test pass is implied. Local toolkit checks
and remote PR/merge state remain separate evidence. No release, package publication,
deployment or observed live acceptance is part of this bootstrap.

## Checkout adoption boundary

Use the clean toolkit worktree or a fresh clone for native skill invocation. The
original dirty checkout and its old local skills are preserved, not synchronized.
Do not force-pull over it. Before later adopting the toolkit there, reconcile its
local `deploy` and `uncorrupter-workflow` copies so duplicate native names do not
remain, preserving unrelated Spec Kit files and the recovery candidate. The validator
fails clearly on those legacy duplicate names. This is a checkout integration concern,
not a reason to publish the unrelated candidate.

## Source delivery reference

[PR #12](https://github.com/jikovec/Uncorrupter/pull/12) carries only this toolkit
change through the authorized source workflow. Consult its live head, checks and
merge record for delivery state; this static handoff does not substitute for them.
The implementation commit is `0af7139d35b452e11f5f200acf4d9abb734b6450`;
subsequent receipt-only updates do not change the validated workflow behavior.
