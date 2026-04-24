# File Uncorrupter

File Uncorrupter is an offline-first corrupted visual-media recovery framework.

This wave moves the repository from a JPEG-only recovery pipeline toward the research blueprint's required shape:

- media-generic intake and signature indexing
- signatures detected anywhere in the blob, not only at byte 0
- richer SQLite evidence model for signatures, candidates, attempts, and multi-artifact outputs
- workspace layout with config snapshots and content-addressed blob storage hooks
- deeper JPEG repair with scattered-segment header rebuild and standard-DHT injection
- baseline FFmpeg-driven video/container probing and salvage
- benchmark command for repeatable local regression runs

## Current scope

Implemented now:

- `scan` command
- `classify` command
- `recover` command
- `benchmark` command
- `report` command
- workspace layout with local config snapshots
- anywhere-signature scanning for image and video/container families
- evidence-rich SQLite run database
- `jpeg-v1` deepened engine
- `baseline-v2` media-generic engine
- Pillow decoder adapter for still images
- FFmpeg/ffprobe-based baseline probing for image/video salvage
- raw winning-candidate persistence

## Commands

### Scan

```bash
file-uncorrupter scan /path/to/input --recursive --all-files --db runs.sqlite3
```

### Classify

```bash
file-uncorrupter classify /path/to/input --recursive --all-files --db runs.sqlite3
```

### Recover

```bash
file-uncorrupter recover /path/to/input /path/to/output --recursive --all-files --db runs.sqlite3 --save-raw-candidates
```

### Benchmark

```bash
file-uncorrupter benchmark /path/to/input /path/to/output --recursive --all-files --db runs.sqlite3 --output-json benchmark.json --output-csv attempts.csv
```

### Report

```bash
file-uncorrupter report --db runs.sqlite3 --run-id 1 --output-json report.json --output-csv attempts.csv
```

## Output notes

- Still-image outputs are normalized to the declared/detected image family where possible.
- Video/container outputs are normalized to robust local artifacts, usually MKV remuxes plus preview frames when FFmpeg can decode them.
- Raw winning candidates are stored under `<output>/_raw_candidates/...` when enabled.
- Workspace state defaults to `<output>/.uncorrupter-workspace/` for recover/benchmark and to the DB directory for scan/classify, unless `--workspace-root` is provided.
