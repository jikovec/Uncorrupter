# Local planning publication — 2026-10-15

## Scope and provenance

Publish the twelve existing files under
[`specs/001-stabilize-multiformat-recovery/`](../specs/001-stabilize-multiformat-recovery/)
and the existing LF-to-CRLF conversions in `LICENSE`,
`VERSIONS/Uncorrupter alfa 0.1.0.py`,
`src/file_uncorrupter/legacy/a_2026_04_01.py`, `tests/a.py`, and
`reports/multi-repo-finalization-2026-07-07.md`.
The owner explicitly selected these files for publication as a task-specific
exception to the default local-only treatment of legacy Spec Kit documents.
This does not change the general repository policy.

The selected files retain their original bytes. Their historical dates, task
checkboxes, approval language, test claims, and local-only statements are preserved
as source context, not adopted as current instructions or verified execution proof.
The related implementation remains a separate change in
[PR #14](https://github.com/jikovec/Uncorrupter/pull/14).
The planning quickstart describes that implementation; it is not a runnable
verification recipe for the current default branch.

## Verification and delivery boundaries

- All seventeen newly published or modified files match the selected local bytes.
- Normalizing CRLF to LF produces exact baseline bytes for the five tracked files;
  no license terms or Python code content changed.
- Both JSON contract files and `docs/agent-index.json` parse successfully.
- Relative Markdown links in the planning snapshot and this handoff resolve.
- Diff whitespace is checked with Git's `cr-at-eol` setting because CRLF is an
  explicitly retained part of this change.
- Recovery tests are not required for documentation and line-ending-only changes.
  Historical test claims in the snapshot have not been rerun by this publication.

The input/output ignore rules were already merged in
[PR #15](https://github.com/jikovec/Uncorrupter/pull/15).
No recovery inputs, derived outputs, databases, or run configurations are included.
No release, package publication, or deployment is part of this change.
