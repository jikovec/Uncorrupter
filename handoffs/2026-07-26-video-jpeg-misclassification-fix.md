# Handoff - 2026-07-26 - Video JPEG Misclassification Fix

## Scope

Prevent declared video files containing embedded or coincidental JPEG markers from being routed into the JPEG recovery engine.

## Current State

- Declared video families now take precedence over JPEG signatures found only inside the payload.
- A JPEG signature at byte zero can still override a misleading video extension.
- Non-video inference now prefers byte-zero evidence, then anywhere-in-file evidence, then the declared extension.

## Files Inspected Or Changed

- Changed `src/file_uncorrupter/classification.py`.
- Changed `tests/test_classification.py`.
- Inspected the classifier, signature index, engine registry, recovery pipeline, CLI, tests, source map, current-state report, and handoff conventions.

## Commands Run

- Focused classification tests: `3 passed`.
- Full test suite: `16 passed`.
- Real-file read-only classification/candidate check: declared MP4 routed to the MP4 family with only the `full_file` candidate; no `MemoryError`.
- `git diff --check` on the source and test changes passed.

## Blockers

- None for the routing fix.

## Next Steps

- Retry folder recovery with `baseline-v2`.
- Treat FFmpeg failures for files without recognizable container structures as normal recovery failures rather than classifier failures.

## Risks And Non-Goals

- This change prevents incorrect JPEG routing; it does not reconstruct missing MP4 atoms or recover encrypted/overwritten payloads.
- Whole-file reads and in-memory candidate payloads remain a separate scalability risk.
