# File Uncorrupter

File Uncorrupter is an offline-first Python CLI for bounded, evidence-preserving recovery of damaged files. It inventories and classifies inputs, runs only explicitly selected recovery goals, writes new artifacts without modifying source files, and records provenance in SQLite, JSONL events, JSON manifests, CSV, and text reports.

The current package is version `0.4.0`. It provides a concrete multi-format recovery base for text, structured text, ZIP/TAR, Open XML and OpenDocument packages, PDF, JPEG and other images, audio/video containers, RTF, and optional-tool archive adapters. Support depth varies by format; the executable capability manifest is authoritative.

> Treat every input as untrusted. Use copies or read-only media for important evidence. Recovery can preserve or expose partial content, but it cannot infer bytes that are no longer present.

## Start Here

- [Current state](docs/current-state.md)
- [Executable capability baseline](docs/capabilities.generated.md)
- [Capability details and improvement roadmap](docs/CAPABILITIES-AND-ROADMAP.md)
- [Benchmark ground-truth schema](docs/BENCHMARK-GROUND-TRUTH.md)
- [CLI reference](docs/api/CLI.md)
- [Security model](docs/security/SECURITY.md)
- [Testing and verification](docs/testing/VERIFICATION.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Documentation index](docs/INDEX.md)

## Installation

Requirements:

- Python 3.11 or newer
- Pillow, installed as the runtime dependency
- Optional: FFmpeg/ffprobe, qpdf, 7-Zip, and LibreOffice for capability probing or adapters documented by the runtime manifest

Install the application:

```powershell
python -m pip install -e .
```

Install development and test dependencies:

```powershell
python -m pip install -e ".[dev]"
```

## Discover Capabilities First

Capabilities are generated from the registered handlers and resolved for the current machine. A goal marked `none` is rejected; it is not silently replaced with a different operation.

```powershell
file-uncorrupter --version
file-uncorrupter capabilities
file-uncorrupter capabilities --format json
file-uncorrupter capabilities --format markdown --output .\capabilities.md
```

The checked-in [capability baseline](docs/capabilities.generated.md) is generated with external tools disabled so it remains deterministic. The live command can expose additional conditional operations when a supported tool is present.

## Common Workflows

Inventory files and signatures only:

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
```

Add classification without recovery:

```powershell
file-uncorrupter classify .\input --recursive --all-files --db .\runs.sqlite3
```

Recover with one or more explicit goals:

```powershell
file-uncorrupter recover .\input .\recovered `
  --recursive --all-files `
  --goal repair --goal extract `
  --db .\runs.sqlite3 `
  --events .\events.jsonl `
  --manifest .\manifest.json `
  --output-csv .\attempts.csv `
  --output-text .\summary.txt
```

If no `--goal` is supplied, `repair` is the only default goal. `repair`, `normalize`, `extract`, `preview`, and `carve` have distinct meanings and output namespaces.

Run recovery with benchmark fields included in the final manifest:

```powershell
file-uncorrupter benchmark .\input .\benchmark-output `
  --recursive --all-files `
  --goal repair --goal extract `
  --ground-truth .\corpus-ground-truth.json `
  --db .\benchmark.sqlite3
```

Ground truth is optional. When supplied, the benchmark validates a versioned safe-relative-path label file and calculates classification/recovery/fidelity accuracy, false-positive and false-negative rates, and per-family aggregates. It always samples main-process RSS during recovery; child-process memory is explicitly excluded. See the [ground-truth schema and metric definitions](docs/BENCHMARK-GROUND-TRUTH.md).

Render reports from a persisted run without reprocessing sources:

```powershell
file-uncorrupter report `
  --db .\runs.sqlite3 `
  --run-id 1 `
  --output-json .\run-1.json `
  --output-csv .\run-1.csv `
  --output-text .\run-1.txt
```

Resume an interrupted run:

```powershell
file-uncorrupter recover .\input .\recovered `
  --recursive --all-files `
  --goal repair --goal extract `
  --db .\runs.sqlite3 `
  --resume 1 `
  --changed-input-policy abort
```

Resume requires compatible input, output, and effective configuration. Unchanged completed files are skipped. Changed sources can be handled with `abort`, `skip`, or `reprocess`; reprocessed artifacts use a new `_resumed/run-NNNNNN/` namespace so earlier evidence is preserved.

## Current Format Boundary

| Family | Current practical boundary |
| --- | --- |
| TXT, Markdown, log, CSV, JSON, XML, HTML | Encoding-aware byte-preserving recovery, span maps, optional UTF-8/newline normalization, and bounded structural diagnostics. Invalid structured content is partial, never labeled validated original. |
| ZIP and TAR | Seekable streaming validation/extraction, checksum/size budgets, local-header ZIP reconstruction, TAR resynchronization, duplicate/path/link/device rejection, and no password cracking. Corrupt-container reconstruction remains a bounded fallback. |
| DOCX/XLSX/PPTX and ODT/ODS/ODP | Streaming package detection/validation, required-part and relationship/manifest checks, inert macro/active-content warnings, conservative rebuild, and separately graded text/media/part artifacts. |
| PDF | Incremental object/xref/trailer/page-tree diagnostics, conservative prefix/EOF/classic-xref reconstruction, partial text extraction, and optional qpdf repair plus qpdf/native validation of the exact output. |
| JPEG | Candidate-based structural repair with decoder validation, plus derivative normalize/preview paths and raw selected-candidate publication when requested. |
| PNG/GIF/BMP/WebP/TIFF | Native structural analysis and conservative repair; seekable Pillow-backed normalization/preview; animation and multipage loss is explicitly graded. |
| HEIF/AVIF/JP2/RAW | Detection and structural/container evidence; decode, preview, and write availability depends on installed Pillow codecs and is reported at runtime. |
| MP4/MOV/Matroska/WebM/AVI/MPEG/FLV/ASF/WMV and WAV/MP3/FLAC/AAC/Ogg | Streaming native structural diagnostics and conservative carving/repair where derivable. When FFmpeg and ffprobe are both available, copy-remux normalize, separately validated stream extraction, and one PNG preview frame are atomically published with stream/timing/coverage/tool evidence. |
| 7z/RAR | Signature detection and inert inspection; bounded extraction is conditional on a recorded 7-Zip-compatible tool. Encryption, solid, and multivolume boundaries remain explicit. |
| RTF | Partial inert text extraction and preview. Formatting and embedded objects are not claimed as recovered. |
| Legacy DOC/XLS/PPT | OLE/macro inspection and conditional headless LibreOffice (`libreoffice` or `soffice`) conversion to a natively validated inert PDF preview. This is preview-only, never editable Office recovery. |

See [Capabilities and roadmap](docs/CAPABILITIES-AND-ROADMAP.md) for operation-level detail and remaining work.

## Safety And Evidence Defaults

- Inputs are opened as immutable byte sources; symlinks and Windows reparse points are rejected.
- Input, output, workspace, and database layouts are checked for unsafe overlap before run state is created.
- Existing destinations are preserved. Artifact publication uses a temporary sibling, flushes it, and atomically publishes it where the filesystem permits.
- Output paths are contained below the selected root and archive paths are normalized. Traversal, links, devices, and duplicate output names fail closed.
- Candidate count/bytes, source/scanned/materialized bytes, decoder time, tool output/artifacts, archive members, expansion ratio, nesting, artifacts, total output, and worker count are bounded. Valid archive/package/PDF/TIFF/media paths stream or use bounded random access; corrupt reconstruction and third-party decoders retain explicit limits.
- External processes use a minimal environment, temporary working directory, bounded output, timeout/cancellation, process-tree cleanup, and recorded tool identity.
- `--require-tool-isolation` fails closed unless the configured `--isolation-wrapper` is available.
- HTML, macros, scripts, OLE objects, document relationships, and archive members are handled as inert content. They are never executed.
- Encrypted inputs are reported. The application does not guess passwords or bypass encryption.
- `--redact-paths` pseudonymizes configured roots in JSONL and final reports. Source-content excerpts are not included by default.

Default resource limits and all CLI switches are listed in the [CLI reference](docs/api/CLI.md).

## Output And Evidence Model

Per-file artifacts are isolated under a deterministic namespace similar to:

```text
<output-root>/
  <relative-source-name>.recovered/
    repair/
    normalize/
    extract/
    preview/
    carve/
  _resumed/
    run-000002/
```

Artifacts are labeled as repaired, normalized, extracted, preview, frame, raw fragment, diagnostics, or manifest. Each persisted artifact records its hash, size, fidelity grade, validation state, source relation, plan/strategy evidence, and relevant tool evidence.

Outcome grades distinguish:

- `validated_original`
- `validated_normalized`
- `partial_content`
- `preview_only`
- `unavailable_dependency`
- `budget_exceeded`
- `cancelled`
- `failed`

SQLite schema version 2 persists run/file lifecycle state, signatures, candidates and strategies, attempts, artifacts, relations, events, budget events, text spans, archive members, document parts, media streams, and tool records.

## Verification Boundary

The local suite uses deterministic synthetic fixtures and mutation helpers. It covers immutable inputs, path containment, no-clobber publication, budgets, source changes, cancellation, resume, schema migrations, capability drift, format handlers, CLI exit policies, reports, and packaging.

Green local tests do not prove recovery of every real-world corrupt file, hostile-file sandboxing, production deployment, cross-platform CI execution, or a measured corpus-wide recovery rate. Those remaining gates are tracked in [Current state](docs/current-state.md) and the [implementation report](reports/2026-08-05-stabilized-multiformat-implementation.md).

## Agent And Documentation Notes

- Future agents should begin with [AGENTS.md](AGENTS.md), [00_Index.md](00_Index.md), [docs/AGENT-INDEX.md](docs/AGENT-INDEX.md), [docs/SOURCE-MAP.md](docs/SOURCE-MAP.md), and [docs/CONNECTIONS.md](docs/CONNECTIONS.md).
- The repository can be used as a local-first plaintext Obsidian vault. `.obsidian/` remains ignored; see [docs/OBSIDIAN.md](docs/OBSIDIAN.md).
- `.agents/` and `.specify/` remain local-only unless a future explicit decision changes that.
- Historical release archives and reports are evidence, not current runtime authority.
