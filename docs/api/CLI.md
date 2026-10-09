# CLI Reference

The public interface is the `file-uncorrupter` command implemented in [`src/file_uncorrupter/cli.py`](../../src/file_uncorrupter/cli.py). There is no HTTP service or remote API in this repository.

## Command Surface

```text
file-uncorrupter [--version] capabilities|scan|classify|recover|benchmark|report
```

| Command | Reads sources | Classifies | Executes recovery | Writes artifacts | Purpose |
| --- | --- | --- | --- | --- | --- |
| `capabilities` | No | No | No | Optional manifest file | Report executable handler/tool truth. |
| `scan` | Yes | No | No | No recovery artifacts | Inventory files and signatures. |
| `classify` | Yes | Yes | No | No recovery artifacts | Add independent extension/signature/structure classification. |
| `recover` | Yes | Yes | Yes | Yes | Execute only requested goals. |
| `benchmark` | Yes | Yes | Yes | Yes | Recover and include benchmark fields in the final manifest. |
| `report` | No source processing | Uses persisted evidence | No | Report files only | Re-render an existing run. |

Human progress is written to stderr. The final summary is JSON on stdout. Machine events, when requested, are a separate JSONL stream.

## Version And Capabilities

```powershell
file-uncorrupter --version
file-uncorrupter capabilities
file-uncorrupter capabilities --format json
file-uncorrupter capabilities --format markdown --output .\capabilities.md
```

`capabilities --format` accepts `text`, `json`, or `markdown`. The manifest identifies each family, variants, extensions, signatures, operations, tool requirements, default limits, encryption/active-content boundaries, output kinds, fixtures, availability, and fidelity statement. The command returns non-zero if the capability quality gate fails.

## Shared Input Options

`scan`, `classify`, `recover`, and `benchmark` share:

```text
input_root
--recursive
--all-files
--db PATH
--workspace-root PATH
--engine NAME
--complete-limit COUNT
--cancel-marker PATH
--events PATH
--allow-risky-layout
--redact-paths
--redaction-salt TEXT
--quiet
```

Behavior:

- Without `--recursive`, only direct files under `input_root` are discovered.
- Without `--all-files`, intake is limited to registered extensions. With it, unknown files are still inventoried but may have no handler.
- Discovery is deterministic and prunes symlink/reparse entries.
- `--complete-limit` stops after the requested number of completed file units.
- A present `--cancel-marker` cancels at a safe checkpoint. The marker is never created by the application.
- `--events` creates a no-clobber JSONL event stream.
- `--quiet` suppresses human progress, not JSON results or durable evidence.
- `--allow-risky-layout` is an explicit opt-in for an otherwise rejected overlapping path layout. It does not disable output containment or input immutability.
- `--redact-paths` replaces configured path roots with deterministic salted identifiers in events/reports.

The default database is `runs.sqlite3`. The default workspace is derived from the output root for recovery commands and from the database directory for read-only processing commands unless `--workspace-root` is supplied.

## Resource Limits

All values must be positive.

| Option | Default | Boundary |
| --- | ---: | --- |
| `--max-source-bytes` | 4 GiB | Largest accepted source. |
| `--max-scanned-bytes` | 4 GiB | Total bytes read through a source budget. |
| `--max-candidates` | 64 | Candidate plans/payloads. |
| `--max-candidate-bytes` | 256 MiB | Candidate payload bytes. |
| `--max-materialized-bytes` | 256 MiB | Bytes copied into memory for one bounded operation. |
| `--max-decoder-seconds` | 30 s | External decoder/tool time. |
| `--max-tool-output-bytes` | 1 MiB | Captured stdout/stderr. |
| `--max-archive-members` | 10,000 | Archive/package members. |
| `--max-archive-member-bytes` | 256 MiB | One expanded member. |
| `--max-decompressed-bytes` | 1 GiB | Total expanded bytes. |
| `--max-expansion-ratio` | 100 | Declared/observed expansion ratio. |
| `--max-nesting-depth` | 3 | Recursive container depth. |
| `--max-artifacts` | 1,000 | Published artifacts. |
| `--max-output-bytes` | 2 GiB | Total output bytes. |
| `--workers`, `--max-workers` | min(4, CPU count) | Bounded concurrent file workers. |

Limits fail before the over-budget materialization or publication. The affected goal/file is labeled `budget_exceeded`; already validated and atomically published artifacts remain recorded.

## scan

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
```

`scan` inventories source identity, size/hash metadata, declared extension kind, and bounded signatures. It deliberately does not add a final classification or execute a handler.

## classify

```powershell
file-uncorrupter classify .\input --recursive --all-files --db .\runs.sqlite3
```

`classify` adds a family/label/confidence decision while preserving extension evidence, byte-0 signature evidence, anywhere-signature evidence, and structural evidence as separate fields. This prevents, for example, a declared video containing an embedded JPEG from being silently routed as a JPEG unless JPEG begins at byte zero.

## recover

```powershell
file-uncorrupter recover .\input .\output `
  --recursive --all-files `
  --goal repair --goal extract `
  --db .\runs.sqlite3
```

Recovery-specific options:

```text
output_root
--goal repair|normalize|extract|preview|carve   (repeatable)
--save-raw-candidates
--resume RUN_ID
--changed-input-policy abort|reprocess|skip
--exit-policy strict|partial-ok|report-only
--manifest PATH
--output-csv PATH
--output-text PATH
--require-tool-isolation
--isolation-wrapper ARG [ARG ...]
```

Goal semantics:

- `repair`: emit a format-compatible reconstruction only when bytes can be derived and validated.
- `normalize`: emit a validated derivative in a canonical encoding/container; it is never mislabeled as the original.
- `extract`: emit independently recoverable members, parts, streams, or text.
- `preview`: emit a human-inspection derivative, labeled `preview_only` when it is not full fidelity.
- `carve`: locate defensible embedded or resynchronized content and preserve partial provenance.

The default is `--goal repair`. Unsupported goals yield explicit unavailable/failed evidence; they are not substituted.

`--save-raw-candidates` publishes only a selected candidate with a concrete payload, currently most relevant to the JPEG candidate engine. It does not dump every speculative candidate.

Reports default to the workspace report directory when explicit paths are omitted. Report/artifact files never silently overwrite existing destinations.

## benchmark

```powershell
file-uncorrupter benchmark .\input .\output `
  --recursive --all-files `
  --goal repair --goal extract `
  --ground-truth .\corpus-ground-truth.json `
  --db .\benchmark.sqlite3
```

`benchmark` uses the same recovery path and safety rules as `recover`. Its manifest adds recovery/partial rates, outcome-grade distribution, fidelity distribution, runtime, input/output/expansion measures, crashes, timeouts, budget stops, cancellations, and sampled main-process RSS.

`--ground-truth` accepts the version 1 JSON contract documented in [Benchmark ground truth](../BENCHMARK-GROUND-TRUTH.md). It supplies safe relative-path labels for expected family, recoverability, acceptable outcome grades, and optional source SHA-256. When labels are present, the manifest includes global and per-family classification/recovery/fidelity accuracy, false-positive rate, false-negative rate, missing/extra files, identity mismatches, and per-file comparisons. Label-dependent metrics remain unavailable when the necessary labels are absent; they are never inferred from the run itself.

RSS sampling records baseline, peak, delta, method, interval, and sample count for the main Python process. `children_included` is false, so the measurement excludes FFmpeg, qpdf, 7-Zip, LibreOffice, and isolation-wrapper child processes.

## Resume

```powershell
file-uncorrupter recover .\input .\output `
  --goal repair `
  --db .\runs.sqlite3 `
  --resume 12 `
  --changed-input-policy abort
```

Resume checks the prior run, input/output roots, and effective configuration. Source identity includes filesystem identity, size, modification time, and hash evidence. Policies:

- `abort`: fail the resumed run when a prior source changed.
- `skip`: record the changed file as skipped.
- `reprocess`: process it into `<output>/_resumed/run-NNNNNN/` so previous outputs are retained.

Unchanged prior files in completed/recovered/partial/skipped states are reused as skipped evidence.

## Cancellation

Cancellation is checked between discovery, analysis, goals, candidates, decoder operations, and publications. External process trees are terminated through the unified process runner. A cancelled run records its state and returns the fatal exit code.

## External Tool Isolation

External tools receive a minimal environment, bounded captured output, a temporary working directory, a timeout, cancellation, cleanup, and recorded resolved path/version.

```powershell
file-uncorrupter recover .\input .\output `
  --goal extract `
  --require-tool-isolation `
  --isolation-wrapper sandbox-command --
```

The wrapper is an argument vector, not a shell command string. When isolation is required and the wrapper cannot be resolved, the process fails closed before the tool launches.

## report

```powershell
file-uncorrupter report `
  --db .\runs.sqlite3 `
  --run-id 12 `
  --output-json .\run-12.json `
  --output-csv .\run-12.csv `
  --output-text .\run-12.txt `
  --redact-paths
```

When `--run-id` is omitted, the latest run is used. `report` reads SQLite only and does not reopen or process source files. It rejects report destinations inside the persisted input root.

## Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Successful under the selected exit policy. |
| `1` | Partial/adverse result under the selected exit policy. |
| `2` | Fatal run, cancellation, invalid layout/configuration, capability quality failure, or unhandled operational error. |
| `3` | No file results, except `report-only` policy treats this as success. |

Exit policies:

- `strict`: success only when no adverse result exists and the run completed.
- `partial-ok`: success when at least one recovery or partial result exists and no fatal run condition occurred.
- `report-only`: completion of reporting is success even when the recovery summary contains adverse/no-result outcomes; fatal conditions remain non-zero.

## Evidence Files

- SQLite schema version 2: lifecycle, files, signatures, candidates/strategies, attempts, artifacts, relations, typed format evidence, events, budget events, and tool records.
- JSONL events: monotonically sequenced lifecycle and evidence events.
- JSON manifest: run configuration, platform/tool evidence, summary, ordered files, artifacts, and optional benchmark metrics.
- CSV: attempt-level review surface.
- Text: compact human summary.

See [Architecture](../architecture/ARCHITECTURE.md), [Security](../security/SECURITY.md), and [Capabilities](../CAPABILITIES-AND-ROADMAP.md) for the boundaries behind these commands.
