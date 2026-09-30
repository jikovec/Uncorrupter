# Source Map

Tags: #repo/source-map #repo/architecture #uncorrupter/recovery

Current source, tests, and package configuration are authoritative for implementation behavior. Historical archives are evidence only.

## Public Interface

- [src/file_uncorrupter/cli.py](../src/file_uncorrupter/cli.py) - CLI parser and command dispatch.
- [pyproject.toml](../pyproject.toml) - package name/version, Python requirement, runtime dependency, pytest configuration, and console entry point.
- [docs/api/CLI.md](api/CLI.md) - current CLI reference.

Commands:

- `scan`
- `classify`
- `recover`
- `benchmark`
- `report`

## Recovery Pipeline

- [pipeline.py](../src/file_uncorrupter/pipeline.py) - scan, classify, recover, score, write outputs, persist evidence.
- [types.py](../src/file_uncorrupter/types.py) - shared data structures.
- [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) - high-level data/control flow.

Primary tests: [test_recovery.py](../tests/test_recovery.py), [test_classification.py](../tests/test_classification.py), [test_db.py](../tests/test_db.py).

## Intake And Signature Detection

- [intake.py](../src/file_uncorrupter/intake.py) - file iteration, byte reads, hashes, extension-derived kind, file records.
- [signature_index.py](../src/file_uncorrupter/signature_index.py) - byte-0 and anywhere-in-blob signature detection.
- [constants.py](../src/file_uncorrupter/constants.py) - signatures, supported kinds, extension mapping, output mappings.

Primary tests: [test_signature_index.py](../tests/test_signature_index.py), [test_classification.py](../tests/test_classification.py).

## Classification

- [classification.py](../src/file_uncorrupter/classification.py) - family, label, confidence, and evidence assignment.

JPEG has the deepest classification/recovery strategy coverage. Other supported families currently use baseline detection and candidate behavior.

Primary tests: [test_classification.py](../tests/test_classification.py), [test_recovery.py](../tests/test_recovery.py).

## Engines

- [engines/base.py](../src/file_uncorrupter/engines/base.py) - recovery engine interface.
- [engines/registry.py](../src/file_uncorrupter/engines/registry.py) - engine registry.
- [engines/jpeg_v1.py](../src/file_uncorrupter/engines/jpeg_v1.py) - JPEG candidate generation.
- [engines/media_v2.py](../src/file_uncorrupter/engines/media_v2.py) - baseline image/video candidate generation and JPEG delegation.

Registered engines: `jpeg-v1`, `baseline-v2`.

## Decoder Adapters

- [decoders.py](../src/file_uncorrupter/decoders.py) - Pillow and optional FFmpeg/ffprobe probing/output adapters.

Related docs: [security/SECURITY.md](security/SECURITY.md), [testing/VERIFICATION.md](testing/VERIFICATION.md).

## Scoring

- [scoring.py](../src/file_uncorrupter/scoring.py) - successful candidate scoring.

## Persistence And Reporting

- [db.py](../src/file_uncorrupter/db.py) - SQLite schema, migrations, run/file/candidate/attempt/output persistence, summaries.
- [reporting.py](../src/file_uncorrupter/reporting.py) - JSON summary and attempts CSV output.

Schema includes `runs`, `files`, `signatures`, `candidates`, `attempts`, `outputs`, and `frames`.

Primary tests: [test_db.py](../tests/test_db.py).

## Workspace

- [workspace.py](../src/file_uncorrupter/workspace.py) - local workspace directories and run-config snapshots.

Recovery/benchmark default workspace state under the output root. Scan/classify default it near the database path unless `--workspace-root` is supplied.

## Test Suite

Current pytest files:

- [tests/test_classification.py](../tests/test_classification.py)
- [tests/test_signature_index.py](../tests/test_signature_index.py)
- [tests/test_db.py](../tests/test_db.py)
- [tests/test_recovery.py](../tests/test_recovery.py)

Legacy source is not part of the pytest suite.

## Historical And Legacy Evidence

- [src/file_uncorrupter/legacy/a_2026_04_01.py](../src/file_uncorrupter/legacy/a_2026_04_01.py) - preserved legacy source evidence.
- [VERSIONS/](../VERSIONS/) - historical release artifacts.
- [docs/reports/archive/](reports/archive/) - historical research.

The former `tests/a.py` duplicate of the legacy script was removed during the 2026-09-30 hygiene baseline because the same historical source is already preserved under `src/file_uncorrupter/legacy/` and `VERSIONS/`; it was not collected by the configured pytest test pattern.
