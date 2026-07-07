# CLI Reference

The public interface in this repository is the `file-uncorrupter` CLI defined in [src/file_uncorrupter/cli.py](../../src/file_uncorrupter/cli.py). There is no HTTP API or route layer in the current repo.

## Common Scan Options

The `scan`, `classify`, `recover`, and `benchmark` commands share these options:

```text
input_root
--recursive
--all-files
--db runs.sqlite3
--workspace-root PATH
--engine baseline-v2
--max-ffmpeg-candidates 12
```

Defaults:

- `--db` defaults to `runs.sqlite3`
- `--engine` defaults to `baseline-v2`
- `--max-ffmpeg-candidates` defaults to `12`
- without `--recursive`, only direct children of `input_root` are scanned
- without `--all-files`, only known media extensions from `EXT_TO_KIND` are scanned

## scan

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
```

Behavior:

- scans input files
- classifies records
- persists run/file/signature/classification evidence
- prints a JSON summary

## classify

```powershell
file-uncorrupter classify .\input --recursive --all-files --db .\runs.sqlite3
```

Behavior:

- scans input files
- classifies records
- persists the same scan evidence as `scan`
- prints a JSON summary

In the current implementation, `scan` and `classify` both classify before persistence.

## recover

```powershell
file-uncorrupter recover .\input .\output --recursive --all-files --db .\runs.sqlite3 --save-raw-candidates
```

Additional arguments:

```text
output_root
--save-raw-candidates
```

Behavior:

- scans and classifies input files
- persists file and signature evidence
- generates candidates through the selected engine
- probes candidates with Pillow or FFmpeg depending on family and availability
- writes the best recovered output when a candidate succeeds
- writes raw winning candidates under `_raw_candidates/` when requested
- persists candidates, attempts, outputs, and artifact metadata
- prints per-file `OK` or `FAIL` lines plus a JSON summary

## benchmark

```powershell
file-uncorrupter benchmark .\input .\output --recursive --all-files --db .\runs.sqlite3 --output-json .\benchmark.json --output-csv .\attempts.csv
```

Additional arguments:

```text
output_root
--save-raw-candidates
--output-json PATH
--output-csv PATH
```

Behavior:

- runs the same recovery path as `recover`
- optionally writes a JSON summary report
- optionally writes attempts CSV
- prints a JSON summary

## report

```powershell
file-uncorrupter report --db .\runs.sqlite3 --run-id 1 --output-json .\report.json --output-csv .\attempts.csv
```

Arguments:

```text
--db runs.sqlite3
--run-id ID
--output-json PATH
--output-csv PATH
```

Behavior:

- reads an existing run database
- defaults to the latest run when `--run-id` is omitted
- optionally writes a JSON summary report
- optionally writes attempts CSV
- prints a JSON summary

## Summary Fields

The JSON summary is produced by `fetch_summary()` in [src/file_uncorrupter/db.py](../../src/file_uncorrupter/db.py). It includes:

- run identity and paths
- engine name
- total files
- recovered count
- failed count
- counts by classification
- counts by family
- counts by anywhere kind
- successful decoder counts
- successful strategy counts
- output type counts
- top failure errors

## Report Files

[src/file_uncorrupter/reporting.py](../../src/file_uncorrupter/reporting.py) writes:

- JSON summary from `fetch_summary()`
- attempts CSV with relative path, strategy, family, phase, decoder, dimensions, duration, frame count, score, and error
