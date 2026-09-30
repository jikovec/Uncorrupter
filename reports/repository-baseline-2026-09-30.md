# Repository Documentation, Governance, Metadata, And Hygiene Baseline - 2026-09-30

## Baseline

- Canonical repository: `jikovec/Uncorrupter`
- Default branch: `main`
- Baseline revision: `70fd1188d3a0ff9ea08e526924eada70532cb582`
- Repository visibility: public
- `main` branch protection observed through GitHub: disabled
- Open pull requests at baseline: none
- Work object: GitHub issue #10
- Related stale-path work: GitHub issue #7

Current source/config/tests and the live GitHub tree were treated as higher authority than historical reports.

The configured local Desktop Commander device was offline during this pass. Local dirty/untracked/ignored worktree state therefore could not be inspected; no local files were mutated.

## Artifact Applicability

| Requested artifact | Decision |
| --- | --- |
| `SECURITY.md` | required and create as GitHub discovery/router to canonical `docs/security/SECURITY.md` |
| `AGENTS.md` | required and improve |
| `README.md` | required and improve |
| `DEPLOYMENT.md` | not applicable; no deployment workflow/target exists |
| `robots.txt` | not applicable; not an indexable web app |
| `LICENSE.md` | represented by established root `LICENSE` (Apache-2.0) |
| `CONTRIBUTING.md` | required and create |
| `CODE_OF_CONDUCT.md` | requires owner/community-policy decision; no standard was already selected |
| `SUPPORT.md` | required and create without SLA promises |
| `CHANGELOG.md` | represented by `docs/releases/CHANGELOG.md` |
| `ARCHITECTURE.md` | represented by `docs/architecture/ARCHITECTURE.md` |
| `DEVELOPMENT.md` | represented by `docs/setup/DEVELOPMENT.md` |
| `TESTING.md` | represented by `docs/testing/VERIFICATION.md` |
| `INSTALLATION.md` | represented by README + developer setup; standalone file not justified |
| `CONFIGURATION.md` | represented by CLI/development docs; no standalone configuration system exists |
| `TROUBLESHOOTING.md` | not applicable; no stable recurring failure catalogue exists |
| `GOVERNANCE.md` | not applicable; no separate governance model is established |
| `MAINTAINERS.md` | not applicable; no separate maintainer roster is established |
| `CODEOWNERS` | not applicable; no verified multi-owner review-routing need exists |
| `THIRD_PARTY_NOTICES.md` | not applicable; no vendored third-party notice set identified |
| `NOTICE.md` | not applicable; no current notice requirement identified |
| `.gitattributes` | required and create for text/binary classification, especially historical ZIPs |
| `.editorconfig` | required and create from observed Python/JSON/TOML/Markdown conventions |
| `CITATION.cff` | not applicable; no formal citation/release metadata exists |
| `sitemap.xml` | not applicable; not an indexable website |

## Created

- `SECURITY.md` - GitHub-discoverable security entry point.
- `CONTRIBUTING.md` - contributor workflow and verification expectations.
- `SUPPORT.md` - supported public routes without promising response times.
- `.editorconfig` - repository formatting defaults.
- `.gitattributes` - source/docs text classification and ZIP binary handling.
- `.github/pull_request_template.md` - lightweight delivery/verification checklist.
- this report.

## Improved Or Corrected

- `AGENTS.md` - authority, work-management, safety, dirty-work, delivery, and validation rules.
- `README.md` - current status/boundaries, docs navigation, policy links, portable command examples, and evidence/output warning.
- `00_Index.md` - removed stale tracked-path claims and duplicate-doc routes.
- `.gitignore` - expanded generated/cache/temp/run-state exclusions while preserving intentional archives/patches.
- `docs/INDEX.md` - canonical-doc map and repository-policy routing.
- `docs/current-state.md` - current tracked tree and live work-ledger model.
- `docs/AGENT-INDEX.md` - canonical start order and delivery/security boundaries.
- `docs/SOURCE-MAP.md` - current test map and legacy boundary.
- `docs/CONNECTIONS.md` - root policy to canonical-doc relationships and GitHub work flow.
- `docs/agent-index.json` - current review date, paths, work-management rules, risks, and omitted-artifact rationale.
- `docs/setup/DEVELOPMENT.md` - platform-neutral setup, generated-file policy, Git workflow.
- `docs/testing/VERIFICATION.md` - exact test files/checks and result vocabulary.
- `docs/security/SECURITY.md` - reporting, support boundaries, path separation, resource limitations, privacy, and no invented guarantees.
- `docs/decisions.md` - recorded the canonical documentation/policy-layout decision.
- `docs/reports/INDEX.md` and `reports/INDEX.md` - corrected routing/inventory.

## Consolidated / Removed

- `docs/architecture.md` - obsolete scaffold stub; canonical architecture remains `docs/architecture/ARCHITECTURE.md`.
- `docs/testing.md` - obsolete scaffold stub; canonical testing remains `docs/testing/VERIFICATION.md`.
- `docs/security-model.md` - obsolete scaffold stub; canonical security remains `docs/security/SECURITY.md`.
- `tests/a.py` - exact historical-script duplicate of preserved legacy evidence; not collected by the configured pytest pattern.

## Preserved Exceptions

`VERSIONS/` and its ZIP files were deliberately retained. Current docs identify them as historical release evidence, so the cleanup request's archive patterns do not override their repository function.

`src/file_uncorrupter/legacy/` and `docs/reports/archive/` were also retained as historical evidence.

No global ignore rule was added for `*.zip`, `*.tar.gz`, `*.patch`, `*.diff`, or `VERSIONS/`.

## Metadata / Legal Boundaries

- Existing root `LICENSE` is Apache License 2.0 and was not changed or duplicated as `LICENSE.md`.
- `pyproject.toml` currently names `OpenAI` in package author metadata. This pass did not change authorship because repository ownership alone is insufficient evidence to rewrite author/legal metadata.
- No `CODE_OF_CONDUCT.md` was selected on the owner's behalf.
- No maintainer, CODEOWNERS, funding, citation, governance committee, or third-party legal notice data was invented.

## Validation

Validation results are finalized after the branch diff and pull request are read back from GitHub.

Expected relevant checks:

- GitHub tree/path consistency
- JSON parse of `docs/agent-index.json`
- changed relative Markdown-link resolution against the tracked tree
- diff whitespace inspection
- repository tests if an executable checkout is available

Local checkout checks (`git status`, `git diff --check`, `python -m pytest`) are unavailable in the current environment unless a repository checkout becomes executable. They must not be reported as passed without execution.

## Delivery Boundary

This task authorizes issue/branch/commit/pull-request delivery. It does not authorize merge, tag, release, publication, deployment, or repository-setting changes.
