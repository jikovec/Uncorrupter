# Source Map

Tags: #repo/source-map #repo/architecture #uncorrupter/recovery

This map connects the current source tree to the product behavior, tests, and docs that describe it. Source, package config, and tests remain the highest-priority truth when this map drifts.

## Public Interface

- [src/file_uncorrupter/cli.py](../src/file_uncorrupter/cli.py) defines the `file-uncorrupter` CLI parser and dispatch.
- [pyproject.toml](../pyproject.toml) declares the package name, package version, Python requirement, runtime dependency on Pillow, pytest configuration, and console script.
- [docs/api/CLI.md](api/CLI.md) documents the CLI surface.

Commands:

- `scan`
- `classify`
- `recover`
- `benchmark`
- `report`

## Recovery Pipeline

- [src/file_uncorrupter/pipeline.py](../src/file_uncorrupter/pipeline.py) orchestrates scan, classification, candidate generation, decoder probing, scoring, output writing, and persistence.
- [src/file_uncorrupter/types.py](../src/file_uncorrupter/types.py) defines shared dataclasses for signatures, file records, classifications, candidates, artifacts, decode results, and recovery outcomes.
- [docs/architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) explains the high-level data flow.

Primary test coverage:

- [tests/test_recovery.py](../tests/test_recovery.py)
- [tests/test_classification.py](../tests/test_classification.py)
- [tests/test_db.py](../tests/test_db.py)

## Intake And Signature Detection

- [src/file_uncorrupter/intake.py](../src/file_uncorrupter/intake.py) iterates input files, reads bytes, hashes data, determines declared kind from extension, and builds file records.
- [src/file_uncorrupter/signature_index.py](../src/file_uncorrupter/signature_index.py) detects byte-0 and anywhere-in-blob signatures.
- [src/file_uncorrupter/constants.py](../src/file_uncorrupter/constants.py) defines file signatures, supported image/video kinds, extension mapping, Pillow output formats, video output extensions, and ISOBMFF brand mapping.

Primary test coverage:

- [tests/test_signature_index.py](../tests/test_signature_index.py)
- [tests/test_classification.py](../tests/test_classification.py)

## Classification

- [src/file_uncorrupter/classification.py](../src/file_uncorrupter/classification.py) assigns family, label, confidence, and evidence.
- JPEG has the deepest classification labels, including missing SOI, missing EOI, missing DHT, structural salvage candidates, weak internal signal, and low signal.
- Other supported families receive baseline container or detected-candidate labels.

Primary test coverage:

- [tests/test_classification.py](../tests/test_classification.py)
- [tests/test_recovery.py](../tests/test_recovery.py)

## Engines

- [src/file_uncorrupter/engines/base.py](../src/file_uncorrupter/engines/base.py) defines the recovery engine interface.
- [src/file_uncorrupter/engines/registry.py](../src/file_uncorrupter/engines/registry.py) registers available engines.
- [src/file_uncorrupter/engines/jpeg_v1.py](../src/file_uncorrupter/engines/jpeg_v1.py) implements JPEG-focused candidate generation.
- [src/file_uncorrupter/engines/media_v2.py](../src/file_uncorrupter/engines/media_v2.py) implements baseline image/video candidate generation and delegates JPEG to `jpeg-v1`.

Registered engines:

- `jpeg-v1`
- `baseline-v2`

Primary test coverage:

- [tests/test_recovery.py](../tests/test_recovery.py)

## Decoder Adapters

- [src/file_uncorrupter/decoders.py](../src/file_uncorrupter/decoders.py) adapts Pillow, FFmpeg, and ffprobe for candidate probing and output writing.
- Pillow is used for supported still-image probing and saving.
- FFmpeg/ffprobe are optional and discovered from `PATH`.
- Video/container recovery can produce remuxed output, preview frames, and frame-set artifacts when local FFmpeg tooling can decode the candidate.

Related docs:

- [Security and local data handling](security/SECURITY.md)
- [Testing and verification](testing/VERIFICATION.md)

## Scoring

- [src/file_uncorrupter/scoring.py](../src/file_uncorrupter/scoring.py) scores successful decoder results.
- Score inputs include candidate priority, decoded dimensions, decoder entropy or video metadata, family match, candidate kind, and classification-specific boosts.

Primary test coverage:

- [tests/test_recovery.py](../tests/test_recovery.py)

## Persistence And Reporting

- [src/file_uncorrupter/db.py](../src/file_uncorrupter/db.py) creates and migrates SQLite schema, starts runs, persists records, and fetches summaries.
- [src/file_uncorrupter/reporting.py](../src/file_uncorrupter/reporting.py) writes JSON summary reports and attempts CSV files.

Main database tables:

- `runs`
- `files`
- `signatures`
- `candidates`
- `attempts`
- `outputs`
- `frames`

Primary test coverage:

- [tests/test_db.py](../tests/test_db.py)

## Workspace

- [src/file_uncorrupter/workspace.py](../src/file_uncorrupter/workspace.py) defines local workspace roots and config snapshots.
- Recovery and benchmark runs default workspace state under the output root. Scan and classify default workspace state near the database path unless `--workspace-root` is provided.

Related docs:

- [Developer setup](setup/DEVELOPMENT.md)
- [CLI reference](api/CLI.md)

## Historical And Legacy Material

- [src/file_uncorrupter/legacy/a_2026_04_01.py](../src/file_uncorrupter/legacy/a_2026_04_01.py) preserves legacy implementation material.
- [tests/a.py](../tests/a.py) is a retained legacy script file.
- [docs/reports/archive/001-deep-research-report.md](reports/archive/001-deep-research-report.md) is historical research evidence.
- [VERSIONS/](../VERSIONS/) contains historical release artifacts and must not be treated as current implementation truth.

## Test Map

- [tests/test_classification.py](../tests/test_classification.py) covers JPEG classification labels.
- [tests/test_signature_index.py](../tests/test_signature_index.py) covers anywhere signature detection for prefixed MP4 data.
- [tests/test_db.py](../tests/test_db.py) covers run summary counts, duplicate candidate persistence, and successful output summaries.
- [tests/test_recovery.py](../tests/test_recovery.py) covers JPEG recovery strategies, candidate generation, standard color tables, and FFmpeg-gated prefixed MP4 recovery.
