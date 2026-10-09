# Native discovery and migration

Canonical skill policy is under `skills/`; adapters contain matching `name` and
`description` plus a repository-relative link. No adapter carries separate rules;
the one exception is the Claude invocation gate below.

- Codex 0.159.2: native `skills/list` with forced reload confirms `.codex/skills/`
  works. This runtime also scans `.agents/skills/`; maintaining both adapter sets
  yields duplicates. Share only `.codex/skills/<name>/SKILL.md` in this repository.
- Claude Code: `.claude/skills/<name>/SKILL.md`; root `CLAUDE.md` imports `@AGENTS.md`.
  The Claude `release`, `deploy` and `publish` adapters also set
  `disable-model-invocation: true`, so Claude Code loads them only on an explicit
  `/release`, `/deploy` or `/publish`. Canonical skills and Codex adapters keep the
  portable name/description metadata, and the validator enforces both forms.
- Every canonical project skill has the same adapters as the baseline workflows.
- Invoke `$build` in Codex or `/build` in Claude, or explicitly request the canonical
  skill by path when a session's cached discovery is stale. Restart/reopen a session
  after checkout changes and verify the displayed path before relying on a name.

`.agents/` and `.specify/` remain local-only. Existing local `deploy` and
`uncorrupter-workflow` copies can conflict with canonical discovery when adopting
this toolkit in an older checkout. Preserve unrelated Spec Kit skills, local metadata
and environment actions. Reconcile those two copies into non-discovered local archives
before using native name routing there; retain canonical adapters only once per name.
Do not force a pull over an unrelated dirty checkout. Use the clean toolkit worktree
until overlapping changes are deliberately reconciled. A fresh clone has no legacy copies.

Old deploy-as-branch-push semantics are superseded: use `push` for source delivery.
`deploy` now means governed deployment to a concrete target; missing deployment
configuration is a real prerequisite. Historical copied guidance does not reinstate
retired semantics. This migration does not publish or delete legacy local files.

Reference sources checked during adoption (2026-10-07):
[OpenAI skill discovery](https://learn.chatgpt.com/docs/build-skills) documents
`.agents/skills/`; the installed runtime additionally supports `.codex/skills/`, as
verified above. [Claude skills](https://code.claude.com/docs/en/skills) and
[Claude imports](https://code.claude.com/docs/en/memory) describe its native paths.
Documentation compatibility, static adapter validation and native runtime discovery
are distinct evidence. Reverify after provider upgrades; record tested versions and
unresolved discovery in a dated handoff. A Codex result does not prove Claude loading.
