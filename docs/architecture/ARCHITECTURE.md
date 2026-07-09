# Architecture

The current architecture is a modular Python CLI pipeline. It is designed around evidence first: every run can persist input records, signatures, classifications, candidates, decoder attempts, outputs, and artifact metadata to SQLite.

Related orientation:

- [Source map](../SOURCE-MAP.md)
- [Connection map](../CONNECTIONS.md)
- [Agent orientation](../AGENT-INDEX.md)

## Data Flow

```text
CLI command
  -> RecoveryPipeline
  -> intake records
  -> signature detection
  -> classification
  -> engine candidate generation
  -> decoder probing
  -> scoring
  -> output writing
  -> SQLite persistence and report export
```

## Command Layer

[src/file_uncorrupter/cli.py](../../src/file_uncorrupter/cli.py) defines the public CLI surface and starts runs. Shared scan arguments are:

- `input_root`
- `--recursive`
- `--all-files`
- `--db`
- `--workspace-root`
- `--engine`
- `--max-ffmpeg-candidates`

`recover` and `benchmark` also take `output_root` and `--save-raw-candidates`. `benchmark` and `report` can write JSON and CSV reports.

## Pipeline Layer

[src/file_uncorrupter/pipeline.py](../../src/file_uncorrupter/pipeline.py) owns orchestration:

- `scan_records`
- `classify_records`
- `recover_one`
- `persist_scan`
- `persist_recovery`

The pipeline selects an engine from the registry, generates candidates, probes candidates, scores successful probes, writes final artifacts, and persists attempts and outputs.

## Intake And Signature Detection

[src/file_uncorrupter/intake.py](../../src/file_uncorrupter/intake.py) builds `FileRecord` values with:

- relative path
- absolute path
- file size
- SHA-256 hash
- declared kind from extension
- byte-0 kind
- anywhere kind
- signature hit summary

[src/file_uncorrupter/signature_index.py](../../src/file_uncorrupter/signature_index.py) scans for signatures anywhere in the blob, including JPEG, PNG, GIF, BMP, TIFF, RIFF/WebP, RIFF/AVI, ISOBMFF brands, EBML, MPEG-TS sync, MPEG-PS, FLV, ASF, and JP2.

## Classification

[src/file_uncorrupter/classification.py](../../src/file_uncorrupter/classification.py) assigns a `Classification` with:

- `family`
- `label`
- `confidence`
- evidence JSON

JPEG has specific structural labels, including:

- `jpeg_missing_soi_internal_structure`
- `jpeg_missing_eoi`
- `jpeg_missing_dht`
- `jpeg_structural_salvage_candidate`
- `jpeg_internal_weak_signal`
- `jpeg_low_signal`

Other families currently receive baseline container or detected-candidate labels.

## Engines

[src/file_uncorrupter/engines/registry.py](../../src/file_uncorrupter/engines/registry.py) registers:

- `jpeg-v1`
- `baseline-v2`

`jpeg-v1` in [src/file_uncorrupter/engines/jpeg_v1.py](../../src/file_uncorrupter/engines/jpeg_v1.py) focuses on JPEG candidate generation:

- full file
- prepend SOI
- append EOI
- SOI-to-EOI and SOI-to-tail windows
- synthetic SOI windows around internal markers
- standard DQT/DHT injection before SOS
- header rebuild from scattered segments
- synthetic SOS rebuilds when SOS is missing
- restart-marker bounded windows

`baseline-v2` in [src/file_uncorrupter/engines/media_v2.py](../../src/file_uncorrupter/engines/media_v2.py) delegates JPEG to `jpeg-v1`, creates generic full-file/signature-offset candidates for non-JPEG images, and creates baseline video/container candidates, including MPEG-TS sync offsets.

## Decoder Adapters

[src/file_uncorrupter/decoders.py](../../src/file_uncorrupter/decoders.py) contains decoder and output adapters:

- Pillow probing and image saving
- FFmpeg image probe/save fallback
- FFmpeg/ffprobe video probe
- FFmpeg remux, preview frame, and frame-set recovery
- output hashing
- video output extension normalization

The module sets `ImageFile.LOAD_TRUNCATED_IMAGES = True` for Pillow.

## Scoring

[src/file_uncorrupter/scoring.py](../../src/file_uncorrupter/scoring.py) scores only successful decoder results. Scores combine candidate priority, decoded dimensions, decoder entropy or video metadata, family match, candidate kind, and classification-specific boosts.

## Persistence

[src/file_uncorrupter/db.py](../../src/file_uncorrupter/db.py) creates and migrates the SQLite schema. Main tables:

- `runs`
- `files`
- `signatures`
- `candidates`
- `attempts`
- `outputs`
- `frames`

`connect()` enables foreign keys, uses WAL mode, creates missing tables, and adds missing columns for older databases.

## Workspace

[src/file_uncorrupter/workspace.py](../../src/file_uncorrupter/workspace.py) defines:

- `blobs/`
- `outputs/`
- `reports/`
- `configs/`

The current pipeline uses workspace creation and config snapshots. The `store_blob()` helper exists for content-addressed blob storage, but the current recovery path primarily writes recovered outputs and optional raw winning candidates.

## Maintenance Notes

- Update [../SOURCE-MAP.md](../SOURCE-MAP.md) when module boundaries or source responsibilities change.
- Update [../CONNECTIONS.md](../CONNECTIONS.md) when architecture-to-test or architecture-to-report links change.
- Treat this file as current architecture documentation; historical architecture notes under [../reports/archive/](../reports/archive/) are evidence, not current truth.
