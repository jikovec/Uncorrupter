# Changelog And Release Notes

This file describes source candidates. It does not assert that a tag, GitHub Release, package publication, deployment, or supported public release exists.

## 0.4.0 - Stabilized Multi-Format Candidate (Unreleased)

Implementation and local verification completed during the 2026-08-05 through 2026-08-08 stabilization work.

### Core

- Reconciled package/runtime version to one source.
- Declared separate runtime and development dependencies.
- Added the defined Windows/Linux and Python 3.11-3.13 CI matrix plus tool-disabled, FFmpeg-present, capability, and package-build gates.
- Added immutable streaming/random-access byte sources and source-change detection.
- Added hierarchical resource budgets and cancellation.
- Added safe layout validation, path containment, collision policies, and atomic no-clobber publication.
- Added one bounded optional-tool runner with minimal environment, temporary work directory, output/time limits, cancellation/tree cleanup, tool identity, and required-isolation fail-closed mode.
- Added deterministic bounded worker coordination.

### Lifecycle And Evidence

- Migrated to SQLite schema version 2.
- Added run/file lifecycle timestamps/state, per-file savepoints, resume queries, and changed-input policies.
- Added candidate content deduplication with separate strategy provenance.
- Added typed artifact relations, text spans, archive members, document parts, media streams, tool records, events, and budget events.
- Added durable JSONL events and atomic JSON/CSV/text reports with path redaction.
- Added versioned benchmark ground truth, global/per-family classification/recovery/fidelity and false-positive/false-negative metrics, plus sampled main-process RSS with an explicit child-process exclusion.

### CLI

- Added `capabilities` and `--version`.
- Made `scan`, `classify`, and `recover` behavior distinct.
- Added repeatable explicit `repair`, `normalize`, `extract`, `preview`, and `carve` goals.
- Added configurable safety/resource limits, cancellation marker, complete limit, workers, resume, changed-input policy, exit policy, manifest/report outputs, redaction, and optional tool isolation.
- Added meaningful exit codes for partial, fatal/cancelled, and no-result runs.
- Separated human progress, stdout JSON, and JSONL machine events.

### Formats

- Added text/structured-text recovery with encoding evidence and byte span maps.
- Added streaming ZIP/TAR safe extraction and conservative bounded reconstruction/resynchronization.
- Added streaming Open XML/OpenDocument validation and separately graded part/content recovery.
- Added incremental PDF diagnostics, conservative repair/extraction, and optional qpdf repair plus exact-output qpdf/native validation.
- Added PNG/GIF/BMP/WebP/TIFF native analyzers and codec-dependent HEIF/AVIF/JP2/RAW boundaries.
- Completed JPEG candidate validation/selection/publication under the new handler path.
- Added streaming video/audio container/header structural analyzers, conservative native repair/carve, and conditional FFmpeg copy-remux/stream-extraction/preview goals with exact output validation and persisted media evidence.
- Added conditional 7z/RAR adapter, inert RTF extraction, and bounded LibreOffice/soffice legacy Office-to-validated-PDF preview.

### Fidelity Corrections

- Preserved the declared-video/embedded-JPEG routing fix so an internal JPEG signature does not override a video at byte zero.
- A valid TAR is validated without needlessly rebuilding it; reconstruction is reserved for structural resynchronization.
- Malformed JSON/XML/inconsistent CSV/unbalanced Markdown is graded partial even when bytes decode losslessly.
- Media normalize/extract/preview are advertised only when FFmpeg and ffprobe are both available; every output is independently validated and hash-correlated before publication.
- Capability output lists only artifact kinds corresponding to advertised operations.
- Normal valid archive/package/PDF/TIFF/media paths no longer require source-sized materialization; explicit bounded fallbacks remain for conservative corrupt reconstruction.

### Testing And Documentation

- Expanded safety, lifecycle, CLI, capability, migration, handler, integration, packaging, process-runner, and mutation tests.
- Added a license-safe public-family fixture/mutation inventory.
- Added a generated tool-disabled capability document with drift protection.
- Replaced the stale media-only documentation with current state, architecture, safety, commands, testing, roadmap, report, and handoff evidence.

### Remaining Release Gates

- Exact-commit GitHub Actions execution is unverified.
- Optional-tool-present Windows/Linux results are incomplete; the reviewed Windows machine verified FFmpeg/ffprobe but lacked qpdf, 7-Zip, and LibreOffice.
- A labeled, license-safe real-world corpus and measured recovery/fidelity/false-positive/peak-memory thresholds are not yet established.
- Renderer-backed PDF/Office validation, vendor RAW depth, real LibreOffice/qpdf/7-Zip matrices, child-process memory measurement, and deeper semantic recovery remain incomplete.
- A dedicated hostile-corpus/fuzzing/security review remains outstanding.

## Prior Version Surfaces

Earlier source and documentation showed inconsistent `0.3.0` package and `0.2.0` runtime values. Those were pre-stabilization states and are superseded by the single `0.4.0` source in `src/file_uncorrupter/__init__.py`.

Historical archives under `VERSIONS/`, root `CHANGELOG/`, and older reports are retained as evidence. They do not override this current source candidate and do not prove a release occurred.

## Verification References

- [Current state](../current-state.md)
- [Executable capabilities](../capabilities.generated.md)
- [Implementation report](../../reports/2026-08-05-stabilized-multiformat-implementation.md)
- [Testing and verification](../testing/VERIFICATION.md)
