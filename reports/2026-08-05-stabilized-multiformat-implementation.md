# Stabilized Multi-Format Recovery Implementation - 2026-08-05

Continuation and final local convergence review: 2026-08-08

Tags: #agent/report #uncorrupter/implementation #uncorrupter/recovery #uncorrupter/testing

## Scope And Outcome

The user requested documentation of File Uncorrupter's current state, capabilities, improvement/stabilization paths, concrete extension base, and possibilities for documents, images, video, archives, TXT, Markdown, and related formats, then asked to implement the fixes.

The local `0.4.0` candidate now contains:

- a bounded immutable-source/atomic-output core;
- explicit capability, inspect, plan, and execute contracts;
- deterministic lifecycle, resume, event, report, and exit semantics;
- implemented handlers across text, archives, package documents, PDF, JPEG/images, media, 7z/RAR, RTF, and legacy Office preview;
- incremental public paths for archives, package documents, PDF, TIFF/images, and media;
- exact-output qpdf, FFmpeg/ffprobe, Pillow, and LibreOffice adapter validation where those operations apply;
- labeled benchmark ground truth, false-positive/negative metrics, per-group aggregation, and main-process RSS sampling;
- exhaustive outcome-grade, determinism, format-variant, and streaming/memory regressions;
- current user, maintainer, agent, architecture, security, testing, report, and handoff documentation.

All locally implementable Spec Kit tasks are complete. The one intentionally open task is exact-commit remote Windows/Linux/Python 3.11-3.13 CI execution. It cannot be honestly completed from an uncommitted dirty worktree and was not authorized through commit/push/workflow actions.

No staging, commit, push, pull request, workflow dispatch, release, package publication, deployment, or remote-setting change was authorized or performed.

## Starting Boundary And Preserved Work

- Branch observed: `main`.
- Original assessment commit reference: `70fd118`.
- User-owned `docs/OBSIDIAN.md` edits were preserved and not modified for this task.
- Concurrent declared-video/embedded-JPEG classification work in `classification.py`, `tests/test_classification.py`, and `handoffs/2026-07-26-video-jpeg-misclassification-fix.md` was preserved and integrated without overwriting ownership.
- `AGENTS.md` contained pre-existing changes and was not normalized or discarded.
- Ignored `.uncorrupter-workspace/`, `output/`, and `single-input/` local data was preserved.
- Historical reports and archives were treated as evidence rather than current runtime authority.

Pre-stabilization deterministic suite: `16 passed in 6.94s`.

## Implemented Core

### Reproducibility And Package Surface

- Version `0.4.0` has one source in `src/file_uncorrupter/__init__.py`; package metadata resolves it dynamically.
- Runtime and `dev` dependencies are declared in `pyproject.toml`.
- `.github/workflows/ci.yml` defines Ubuntu/Windows, Python 3.11/3.12/3.13, deterministic external-tools-disabled tests, capability/doc consistency, package build, and a separate Ubuntu FFmpeg-present job.
- Package tests check the version source, dependencies, workflow shape, and build metadata.

### Immutable Source And Streaming Interface

- `FileByteSource` records file identity and exposes bounded random reads, prefix/tail access, streaming chunks, SHA-256, lazy slices, and explicit unchanged checkpoints.
- `SourceReader` is a read-only seekable `io.RawIOBase` adapter over the immutable source. Every read retains identity and scan-budget enforcement.
- Symlinks and Windows reparse points are rejected.
- Source identity is checked before/during reads and after recovery.

### Bounded Execution And Publication

- `ResourceLimits` and hierarchical `BudgetTracker` cover source/scan/materialization, candidates, decoder/tool time and output, tool artifacts, archive members and expansion, nesting, artifacts, total output, and workers.
- Budget consumes fail before exceeding a limit and persist the responsible counter/evidence.
- Cancellation is integrated through discovery, analysis, plans, decoders/tools, and publication.
- Input/output/workspace/database overlaps are rejected before run creation unless explicitly opted into the narrow risky-layout policy.
- `AtomicArtifactWriter` contains output paths, preserves existing artifacts, uses exclusive temporary siblings, validates, flushes, hashes, and atomically publishes.
- The external-process runner uses no shell, minimal environment, private temporary working directory, timeout, captured-output limit, cancellation/process-tree cleanup, tool identity, and optional required isolation.

### Coordinator, Lifecycle, Resume, And Evidence

- Registered handlers own public variants and implement capability, read-only inspection, bounded plans, and execution.
- Goals are distinct: `repair`, `normalize`, `extract`, `preview`, and `carve`; `repair` is the only default.
- Deterministic bounded workers preserve stable result order.
- SQLite schema version 2 stores run/file lifecycle, source identities, signatures/classification, candidate payloads and strategies, attempts, outputs/artifact relations, frames, events, budgets, tools, text spans, archive members, document parts, and media streams.
- Per-file transactions retain completed evidence if a later file fails.
- Resume creates a linked new run, verifies configuration/source identity, reuses unchanged completed evidence, and routes changed inputs through explicit `abort`, `skip`, or `reprocess` policy.
- Reprocessed artifacts use `_resumed/run-NNNNNN/`; previous evidence is preserved.

### Reports And Exit Semantics

- JSONL events are exclusive, monotonically sequenced, and durably flushed.
- JSON manifests, attempt CSV, and text summaries are deterministic, atomic, no-clobber, and optionally path-pseudonymized.
- CSV includes file status and outcome grade; text reports include the outcome-grade distribution.
- Every surface distinguishes all eight grades: `validated_original`, `validated_normalized`, `partial_content`, `preview_only`, `unavailable_dependency`, `budget_exceeded`, `cancelled`, and `failed`.
- A requested goal with no available plan now records `unavailable_dependency`/file status `unavailable` rather than generic failure.
- `strict`, `partial-ok`, and `report-only` policies are exhaustively tested; fatal errors remain fatal.

## Implemented Format Paths

### Text And Structured Text

- UTF-8/16/32 BOMs, Windows-1252, and ISO-8859-1 evidence.
- Exact/replacement/skipped byte spans and output-to-source offset maps.
- JSON/XML/CSV/HTML/Markdown diagnostics without execution.
- Separate extraction, UTF-8/newline normalization, preview, partial repair, and carve artifacts.
- Invalid structure remains `partial_content` even when every byte decodes.

### ZIP, TAR, And Package Documents

- Valid ZIP/TAR paths now use the seekable source adapter; members stream through CRC/size validation and atomic extraction.
- Traversal, duplicate names, links, devices, unsupported special files, encryption, member size/count, decompression, and expansion boundaries are explicit.
- ZIP local-header reconstruction and TAR resynchronization remain bounded complete-source fallbacks only for damaged containers.
- DOCX/DOCM/XLSX/XLSM/PPTX/PPTM/ODT/ODS/ODP stream through ZIP inspection.
- XML parts use pull parsing, reject DTD/entities, clear elements, and cap accumulated extracted text.
- Required parts, content types/manifests, relationships, external links, macros, active XML, media, and embeddings are recorded; outputs stream atomically.
- Conservative corrupt-package rebuild remains bounded.

### PDF

- Added incremental 1 MiB chunk scanning with bounded overlap/tail state for header, explicit objects, streams, pages, xref/trailer/startxref/EOF, encryption, embedded files, and actions.
- qpdf reads the immutable source path, emits a temporary repaired candidate, and runs `--check` on that exact candidate.
- The candidate then passes the native incremental validator; its hash is correlated with streamed atomic publication.
- Native prefix/EOF/classic-xref repair and text fallback remain bounded materialization paths. Oversized invalid inputs report the unavailable fallback instead of allocating unbounded memory.
- Cancellation, timeout, output-size, and tool-run evidence is preserved.

### JPEG And Other Images

- JPEG candidate generation is capped by count/bytes, structurally scored, independently decoded, deterministically selected, and actually published.
- PNG/GIF/BMP/WebP/TIFF native structures and conservative repairs are implemented.
- Pillow inspection receives the seekable source adapter; normalization/preview outputs are written to temporary files, validated, and streamed atomically rather than accumulated as an encoded `BytesIO`.
- Multipage/animation and first-frame/page derivatives are explicitly graded.
- HEIF/AVIF/JP2/RAW/DNG availability stays dependent on installed codecs/plugins.

### Video And Audio

- Native streaming/random-access analysis covers MP4/MOV, EBML/Matroska/WebM, RIFF AVI/WAV, MPEG-TS continuity, MPEG-PS, FLV, ASF/WMV, MP3, FLAC, AAC, and Ogg.
- Prefix removal and RIFF-size correction stream the source into atomic publication.
- With both FFmpeg and ffprobe present, handler plans expose:
  - `normalize`: copy-remux all streams to MKV/MKA without transcoding;
  - `extract`: independently output supported video/audio/subtitle streams as Matroska streams;
  - `preview`: output one PNG video frame.
- FFmpeg consumes the immutable source path directly, except prefix-damaged input is streamed to a temporary file after the prefix.
- Every temporary output is ffprobe-validated, hashed, streamed atomically, and checked against the published hash.
- Stream inventory, timing, timestamp continuity, decoded coverage, warnings, dimensions/duration/frames, tool runs, artifact relations, and fidelity are persisted.
- Tool absence produces no plan/unavailable dependency; a one-frame preview and copy-remux are never mislabeled as full reconstructed media.

### 7z/RAR, RTF, And Legacy Office

- 7z/RAR detection, bounded tool listing/extraction, safe paths, and encrypted/solid/multivolume evidence remain conditional on 7-Zip.
- RTF extraction is inert and partial; object markers are warnings.
- DOC/XLS/PPT OLE and macro/active-content signals are inspected without execution.
- When LibreOffice is present, headless safe/private-profile conversion emits only a PDF preview. The PDF must pass native header/EOF/xref/object validation before atomic publication.
- Both `libreoffice` and Windows `soffice` executable names are resolved.
- Output is `preview_only`, never editable Office recovery.

## Benchmark And Coverage Fixes

- `src/file_uncorrupter/benchmarking.py` validates a maximum-16-MiB, maximum-100,000-entry version 1 ground-truth JSON file.
- File keys must be safe relative paths and are duplicate-checked case-insensitively.
- Optional labels cover family, recoverability, acceptable outcome grades, and source SHA-256.
- Evaluation emits global and per-family classification/recovery/fidelity accuracy, false-positive/false-negative rate, missing/extra files, identity mismatch, and per-file detail.
- The benchmark samples main-process RSS on Windows, `/proc` Linux, or `resource` fallback and records method, interval, samples, baseline, peak, and delta.
- Child-process memory is explicitly excluded.
- Fixture/mutation inventory now covers every public variant as applicable, including valid suffix/media-type checks and explicit gap failure.
- Two independent runs compare normalized manifest order, selected artifact identities/hashes, and strategy order while excluding only run IDs/timestamps.

## Streaming Regression Evidence

`tests/test_streaming_handlers.py` proves:

- ZIP, DOCX, PDF, TIFF preview, and AVI repair public paths work when the source exceeds a 32-byte materialization ceiling;
- each consumes zero materialized source bytes;
- a 16 MiB stored ZIP validates through the streaming path with a traced Python allocation peak below 12 MiB.

This does not claim constant memory for decoded images/frames, corrupt-container fallback, or child tools.

## Tool Evidence On Reviewed Machine

| Tool | State |
| --- | --- |
| FFmpeg | Available: `8.1.2-full_build-www.gyan.dev` |
| ffprobe | Available: `8.1.2-full_build-www.gyan.dev` |
| qpdf | Unavailable |
| 7-Zip command `7z` | Unavailable |
| LibreOffice commands `libreoffice` and `soffice` | Unavailable |

qpdf, 7-Zip, and LibreOffice tool-present behavior is covered by deterministic controlled adapters/fakes, not by real installed binaries in this local evidence. The distinction is intentional.

## Verification Results

Final post-documentation local verification:

- deterministic external-tools-disabled full suite: `154 passed, 1 skipped, 1 warning in 14.93s`;
- skip: `tests/test_recovery.py:152`, FFmpeg-required legacy recovery path while tools were deliberately disabled;
- warning: Python `zipfile` reports the deliberately duplicated `same.txt` hostile fixture;
- external-tool-present full local suite: `155 passed, 1 warning in 15.00s`;
- focused real FFmpeg media/recovery/multiformat suite: `21 passed in 7.21s`;
- focused capability/CLI/external-adapter suite after `soffice` fallback: `30 passed in 7.79s`;
- focused streaming handler suite: `6 passed`;
- focused existing handler suite during streaming refactor: `42 passed, 1 warning`;
- `python -m compileall -q src tests`: exit `0`;
- `python -m build`: built `file_uncorrupter-0.4.0.tar.gz` and `file_uncorrupter-0.4.0-py3-none-any.whl` successfully;
- CLI runtime: `file-uncorrupter 0.4.0`;
- tool-present capability output on this Windows machine reports media normalize `baseline`, extract/preview `partial`, and media availability `available`;
- tool-disabled capability baseline drift test passed;
- JSON parsing passed for `docs/agent-index.json` and both Spec Kit schema files;
- current Markdown targets and balanced code fences passed for 37 files;
- CI YAML parsed with the already-established temporary verification dependency set; the project `.venv` itself does not contain PyYAML, so the first direct `.venv` YAML import was unavailable and was rerun through that dependency set;
- `git diff --check`: exit `0`; Git emitted only Windows LF-to-CRLF notices.

A workflow definition is not exact-commit CI execution proof.

Exact primary commands:

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = '1'
.\.venv\Scripts\python.exe -m pytest -q -rs

Remove-Item Env:\UNCORRUPTER_DISABLE_EXTERNAL_TOOLS -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m pytest -q -rs tests\test_media_handlers.py tests\test_recovery.py tests\test_multiformat_integration.py

.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe -m file_uncorrupter.cli --version
.\.venv\Scripts\python.exe -m file_uncorrupter.cli capabilities --format json
.\.venv\Scripts\python.exe -m json.tool .\docs\agent-index.json
git diff --check
```

## Spec Kit Convergence

Artifacts are under `specs/001-stabilize-multiformat-recovery/`. Specification, plan, contracts, tasks, checklist, implementation, analysis, and convergence workflows shaped the behavior and evidence contracts.

Completed convergence tasks include qpdf output repair/validation, FFmpeg goals/evidence, legacy preview adapter, labeled benchmarks/RSS, public-variant fixtures, two-run determinism, exhaustive outcome reports/exit policies, and streaming handler conversion.

Only `T094` remains open: clean-install remote Windows/Linux/Python 3.11-3.13 and optional-tool gates on an exact commit. No exact committed candidate or remote action exists in this task, so marking it complete would be false.

## Evidence Boundary And Remaining Risks

Implemented and locally tested:

- the named source/configuration/documentation;
- deterministic synthetic fixtures, controlled optional-tool adapters, local CLI/database/artifact integration;
- real installed FFmpeg/ffprobe paths;
- package build and tool-disabled capability baseline.

Still unverified or intentionally incomplete:

- exact-commit GitHub Actions execution on Windows/Linux/Python 3.11-3.13;
- real qpdf, 7-Zip, LibreOffice, optional Pillow codec, and isolation-wrapper matrices;
- a broad licensed real-world corruption corpus and statistically useful support thresholds;
- renderer-backed PDF/Office page/semantic fidelity;
- child-process and whole process-tree memory/CPU/IO measurement;
- hostile-corpus fuzzing and independent defensive security review;
- release, publication, deployment, or live-service behavior.

## Git And External Actions

- Files were edited locally only.
- No stage, commit, branch change, push, PR, workflow dispatch, tag, release, package publication, deployment, or remote-setting change occurred.
- No live service or deployment target was checked.
