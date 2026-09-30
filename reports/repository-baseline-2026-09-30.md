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

## Ignore Rules

`.gitignore` now excludes common Python caches, test/type/lint caches, virtual environments, build/coverage/dependency output, local SQLite state, `.uncorrupter-workspace/`, `_raw_candidates/`, root temp/backup directories, editor/OS debris, and logs/backups.

It deliberately does not ignore `VERSIONS/`, `*.zip`, `*.tar.gz`, `*.patch`, or `*.diff` globally because those patterns can represent intentional repository evidence or inputs.

## Conflicts Corrected

- Current-state and root project-map documentation no longer present absent `CHANGELOG/`, `DOCUMENTATION/`, or `results/` directories as current tracked areas.
- Agent/testing/security navigation now routes to one canonical document per subject instead of competing scaffold stubs.
- Old local-worktree claims about dirty `VERSIONS/` files were removed from current-state surfaces; historical reports retain those observations as historical evidence.
- Current tests are represented by the four configured `tests/test_*.py` files; the duplicate legacy script is no longer presented as a current test artifact.

## Validation

### Passed

- GitHub compare: branch is ahead of baseline by one commit before this report-finalization commit, with the baseline commit as merge base.
- GitHub tree readback: all intended new/current canonical files are present; `docs/architecture.md`, `docs/security-model.md`, `docs/testing.md`, and `tests/a.py` are absent.
- Historical evidence readback: the tracked `VERSIONS/` ZIP archives and `src/file_uncorrupter/legacy/a_2026_04_01.py` remain present.
- `docs/agent-index.json` parses as JSON after branch readback.
- Relative links in every changed Markdown file resolve against the committed GitHub tree.
- Every changed text file checked has no trailing whitespace and ends with a final newline.
- Pull-request patch readback reports 27 changed files and no changes under `VERSIONS/`, current `src/file_uncorrupter/` source, `pyproject.toml`, or the four current `tests/test_*.py` modules.
- Added-line whitespace scan of the pull-request patch found no trailing whitespace.

### Unavailable

The configured local Desktop Commander device was offline, and the current execution container could not reach GitHub directly to obtain an executable checkout. Therefore these repository-local commands were not run and are not reported as passing:

- `git status --short --branch`
- `git diff --check`
- `python -m pytest`

### Not Applicable / Not Run

- Deployment verification: not applicable; no deployment workflow exists.
- Website checks (`robots.txt`, sitemap): not applicable; this is not a deployed/indexable website repository.
- GitHub Actions: no workflow run was associated with the initial PR head commit.

## Git / GitHub State

- Branch: `docs/repository-baseline-20260930`
- Initial implementation commit: `ff4f2ad7a263e1c0b647d9ad09e56cf5fbea385e`
- Pull request: #11, `Establish repository documentation and hygiene baseline`
- Pull request state during validation: open, unmerged
- Base branch: `main` at `70fd1188d3a0ff9ea08e526924eada70532cb582`
- Merge: not performed
- Release/publication/deployment/tag: not performed

The final head SHA changes when this report-finalization commit is added to the same branch; PR #11 remains the delivery object.

## Remaining Owner Decisions

- Decide whether to adopt a `CODE_OF_CONDUCT.md`; no standard was selected on the owner's behalf.
- Confirm or correct package author/legal metadata in `pyproject.toml` if `authors = [{name = "OpenAI"}]` is not intended; this pass deliberately did not infer authorship.

The package-version mismatch, pytest dependency policy, and product/security implementation gaps remain tracked as implementation work in the live issue ledger rather than being converted into owner-policy decisions here.

## Delivery Boundary

This task authorized issue/branch/commit/pull-request delivery. It did not authorize merge, tag, release, publication, deployment, or repository-setting changes. PR #11 is intentionally left open.
