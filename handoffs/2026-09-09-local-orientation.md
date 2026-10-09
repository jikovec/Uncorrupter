# Local Project Orientation — 2026-09-09

## Result and authority

Updated the existing [project overview/card](../docs/PROJECT-OVERVIEW.md), [agent workflow](../docs/agent-workflow.md), root/agent/handoff navigation, current-state orientation note and machine-readable agent index. Reused existing local skills, Spec Kit and manual environment actions. No product behavior or historical evidence was rewritten.

The catalogue checkout is now accessible through the current workspace alias; machine-specific paths remain in the external catalogue. Repository owner/default branch/public visibility were confirmed by a successful GitHub connector metadata read. Local HEAD and live `git ls-remote origin refs/heads/main` both identify `70fd1188d3a0ff9ea08e526924eada70532cb582`. The substantial dirty/untracked 0.4.0 candidate is separate from that committed state. Git index/staging was not changed.

The supplied historical attachment describes older committed behavior. Current source resolves its version mismatch and missing dev-dependency issues, implements multi-format handlers, source/layout/budget controls, differentiated scan/classify, capabilities, lifecycle/resume, and optional path pseudonymization. Package author metadata still says OpenAI; repository ownership is jikovec. Do not infer a metadata edit or branch cleanup instruction from the attachment.

## Inspection and preservation

Read repository AGENTS.md, required orientation/decision/source/connection documents, current implementation report/handoff, pyproject, relevant source/tests, existing workflow skill/guide, local skill/environment definitions, ignore rules, Git state, workflow and hook inventory. No AGENTS.md was present in the inspected canonical ancestor chain. One independent read-only source audit corroborated scope and command contracts.

Before editing, captured hashes for 130 tracked/untracked non-ignored files and byte-preserving copies of the seven existing documentation files selected for edits in temporary local storage. Changes are scoped additions to existing documents plus this handoff; no checkout reset, stash, synchronization, historical normalization, source edit, original-data inspection, or relocation occurred. A clean worktree from HEAD would omit the uncommitted implementation being documented, so the scoped documentation edits were made against the accessible candidate.

## Validation

- Source-backed commands compared with pyproject, CLI, existing command docs and environment actions.
- JSON machine index parsed with the available bundled Node runtime; changed relative Markdown file links and machine-index important paths checked for existence.
- Task delta checked against pre-edit byte copies, including this new handoff. Repository-wide `git diff --check` already failed before edits with 10,534 diagnostic lines, including inherited CRLF/trailing whitespace in .gitignore and historical source; no cleanup was attempted.
- Pre-edit hash comparison verifies only the seven planned existing documentation files changed and this handoff was added; unrelated tracked/untracked bytes remain unchanged.
- Python/python3, installed file-uncorrupter, pytest, uv, FFmpeg/ffprobe, qpdf and 7z are unavailable on PATH. LibreOffice resolves, but version/adapter execution is unverified. No project runtime lock or Nix development definition was found. Test actions are configured, not runnable in this shell.
- Python JSON command, runtime capability output, pytest, compile and build were not run. No dependencies were installed and no substitute runtime was used for application validation. Prior Windows green-test counts remain historical evidence, not a current-host pass.

## Connectors and publication

GitHub connector repository metadata read succeeded; local Git/shell are usable. Atlassian and Cloudflare tool definitions are exposed but their connections were not tested and no UNCorrupter integration is established. PDF/document skills are available only as task-dependent artifact tooling. No plugins were installed, accounts connected, integrations enabled, tickets created, or messages sent.

The local untracked `.github/workflows/ci.yml` defines push/pull_request tests/build on Windows/Ubuntu Python 3.11–3.13 and a separate Ubuntu FFmpeg job. It contains no package/release upload, Pages or deployment step. Hook inventory contains samples only; no core.hooksPath override was found. This does not audit external account/host automation. Reinspect triggers before any future separately authorized delivery.

No staging, commit, push, PR, workflow dispatch, release, package publication, deployment or remote settings change occurred. No exact-candidate CI, deployed identity or live acceptance was established. Local orientation work is complete without publication.

## Concrete remaining work

1. Establish the intended supported Python development runtime on this host, then use the existing dev-extra install and focused capability/packaging command. No new command system or plugin is needed.
2. Owner decision: retain or correct package author metadata `OpenAI`; it is not repository ownership truth.
3. Keep broader corpus, optional-tool matrices, whole-process-tree resource evidence, isolation/fuzzing/security review and fidelity depth as engineering gaps.
4. If publication is later requested, inventory the preserved candidate separately, inspect triggers again, and correlate checks to the exact authorized commit. Remote dev ancestry, branch cleanup, protection and distribution policy remain outside this task; the old attachment is not fresh evidence for them.
