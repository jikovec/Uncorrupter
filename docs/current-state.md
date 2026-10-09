<!-- codex-memory-scaffold:current-state -->
# Current State

Last source and local verification review: 2026-08-08

Current authority order is source and `pyproject.toml`, executable tests, the runtime capability manifest, the checked tool-disabled capability baseline, and then this narrative. Historical reports and release archives are evidence only.

## Orientation review — 2026-09-09

The [current project card](PROJECT-OVERVIEW.md#current-project-card--2026-09-09) and [handoff](../handoffs/2026-09-09-local-orientation.md) record the accessible local 0.4.0 candidate, unchanged committed main, existing agent setup, and current host prerequisites. Python is not available on PATH; this review did not rerun runtime tests or build. The Windows results below remain dated historical evidence.

## Executive State

File Uncorrupter `0.4.0` is an offline-first, bounded, multi-format recovery framework. It inventories and classifies untrusted files, plans only an explicitly requested recovery goal, publishes derived artifacts without changing source bytes, and persists evidence sufficient to distinguish a validated result from a partial result, preview, unavailable dependency, budget stop, cancellation, or failure.

The local candidate now has a concrete recovery base rather than a collection of media-specific scripts:

- immutable seekable/streaming sources with identity checks;
- one format-handler contract and deterministic registry;
- explicit `repair`, `normalize`, `extract`, `preview`, and `carve` goals;
- contained, budgeted, atomic, no-clobber publication;
- durable SQLite schema version 2, JSONL events, JSON manifests, CSV, and text reports;
- cancellation, bounded workers, resume, changed-source policy, and machine-readable exit policy;
- native handlers plus conditional qpdf, FFmpeg/ffprobe, 7-Zip, LibreOffice, and Pillow-codec paths;
- a labeled benchmark input contract, false-positive/false-negative metrics, per-family aggregation, and sampled main-process RSS;
- incremental public paths for ZIP/TAR, package documents, PDF, TIFF/images, and media, with bounded whole-file fallback only where conservative reconstruction still requires it.

It remains an unreleased experimental recovery tool. Local tests are strong evidence for the implemented contracts, but they are not proof of every real-world corruption, a hostile-file sandbox, remote cross-platform CI, a public release, or deployment.

## Current Local Evidence

Observed on Windows with Python 3.11.9:

| Evidence tier | Result |
| --- | --- |
| Deterministic external-tools-disabled suite | `154 passed, 1 skipped, 1 warning` in 14.93 s. The skip is the legacy FFmpeg recovery test; the warning is the intentional duplicate-ZIP fixture. |
| Tool-present full local suite | `155 passed, 1 warning` in 15.00 s. |
| Focused real-media suite | `21 passed` in 7.21 s using installed FFmpeg/ffprobe. |
| Installed media tools | FFmpeg `8.1.2-full_build-www.gyan.dev`; ffprobe `8.1.2-full_build-www.gyan.dev`. |
| Optional tools not present on this machine | qpdf, 7-Zip, LibreOffice (`libreoffice` and Windows `soffice` command names). |
| Package build | Source distribution and pure-Python wheel for `0.4.0` built successfully. |

The exact commands and evidence boundary are in the [implementation report](../reports/2026-08-05-stabilized-multiformat-implementation.md). GitHub Actions is defined for Windows/Linux and Python 3.11-3.13, but no exact-commit remote run was authorized or observed. The workflow file is therefore configuration, not execution proof.

## Stabilized Core

### Source And Output Safety

- `FileByteSource` provides bounded reads, streaming iteration, streaming SHA-256, lazy slices, and a read-only seekable adapter for standard parsers.
- File identity is checked before and during reads and again after recovery. A changed source fails closed.
- Symlinks and Windows reparse points are rejected during deterministic intake.
- Input, output, workspace, and database paths are checked for unsafe overlap before run creation.
- Output names and archive member paths are normalized and contained below the selected root.
- Publications use exclusive temporary siblings, flush, validation where applicable, and atomic replace/link semantics without overwriting an existing destination.

### Bounded Execution

- Limits cover source bytes, scanned bytes, materialized bytes, candidate bytes/count, decoder time, captured tool output, tool artifacts, archive members, decompressed bytes, expansion ratio, nesting, artifacts, total output, and workers.
- Budgets are hierarchical and fail before the over-limit consume or publication.
- Cancellation checkpoints cover discovery, analysis, planning, execution, tools, and publication; external process trees are terminated.
- External processes use argument vectors without a shell, a minimal environment, temporary working directory, timeout, bounded captured output, cleanup evidence, resolved executable/version evidence, and optional required isolation.
- No operating-system sandbox is bundled. `--require-tool-isolation` fails closed unless an explicitly configured wrapper exists.

### Lifecycle And Evidence

- SQLite schema version 2 uses additive migration, run/file lifecycle states, per-file savepoints/commits, source identity, and resume lineage.
- Resume reuses only compatible unchanged evidence. Changed sources follow explicit `abort`, `skip`, or `reprocess` policy; reprocessed artifacts enter a new `_resumed/run-NNNNNN/` namespace.
- Candidate payload identity is separated from strategy provenance, so duplicate bytes do not erase how they were derived.
- Persisted relations cover attempts, outputs, validators, transformations, text spans, archive members, document parts, media streams, tools, budgets, and events.
- JSONL sequences and report ordering are deterministic. Reports can pseudonymize configured paths and do not include source excerpts by default.

## Format Capability Matrix

Operation depth is deliberately narrower than extension recognition. `validated`, `baseline`, `partial`, and `none` describe executable operations, while outcome grades describe a particular attempt. The live `file-uncorrupter capabilities --format json` output is authoritative for the current machine.

| Family and variants | Implemented now | Important boundary |
| --- | --- | --- |
| Plain/structured text: TXT, Markdown, log, CSV, JSON, XML, HTML | UTF-8/16/32 BOMs, Windows-1252/Latin-1 evidence, exact/replacement/skipped byte spans, offset maps, structure diagnostics, inert extraction, UTF-8/newline normalization, preview, and partial carve/repair. | Missing language or bytes are never invented. Malformed structures remain partial even when decoding is lossless. Very large text still uses the explicit materialization ceiling. |
| Native archives: ZIP, TAR | Seekable streaming validation/extraction, CRC/size checks, traversal/duplicate/link/device rejection, member/decompression/ratio limits, ZIP local-header reconstruction, and TAR resynchronization. | Encryption is reported, not cracked. Corrupt-container reconstruction is the bounded materialization fallback; valid containers do not require whole-source memory. |
| Package documents: DOCX/DOCM, XLSX/XLSM, PPTX/PPTM, ODT/ODS/ODP | Streaming package inspection; required parts, manifests, content types, relationships, macros, external relationships, active XML, embeddings; safe part/text/media extraction; conservative package rebuild. | Full Word/Excel/PowerPoint/LibreOffice rendering and semantic fidelity are not proven. Corrupt-package rebuild remains bounded. |
| PDF | Incremental header/object/stream/xref/trailer/startxref/EOF/page/encryption/active-content analysis, partial text extraction, native prefix/EOF/classic-xref repair, and optional qpdf repair plus qpdf and native validation of the exact output. | No page renderer, OCR, font reconstruction, full object-stream/xref-stream recovery, or password bypass. Native reconstruction requiring the complete source is bounded and explicitly unavailable above that limit. |
| JPEG | Bounded candidate strategies, structural evidence, independent Pillow decode validation, deterministic selection, repair, normalize, preview, and selected raw-candidate publication. | Severe entropy/scan corruption is heuristic; validation proves decodability, not perfect original pixels. |
| PNG, GIF, BMP, WebP, TIFF | Native chunk/block/header/IFD analysis and conservative repair; seekable Pillow inspection; atomic normalized image and PNG preview output. | Decoder frames/pages may still occupy memory; first-frame/page derivatives are labeled partial/preview rather than full fidelity. |
| HEIF/AVIF, JP2, RAW/DNG | Detection and codec/plugin-dependent inspection/normalization/preview where Pillow supports the installed codec. | Vendor RAW repair and stable cross-machine codec/write support are not implemented. Runtime capability evidence controls availability. |
| Video/audio: MP4/MOV, MKV/WebM, AVI, MPEG-TS/PS, FLV, ASF/WMV, WAV, MP3, FLAC, AAC, Ogg | Streaming/random-access native container diagnostics and conservative prefix/RIFF-size repair/carve. With FFmpeg and ffprobe: copy-remux normalization to Matroska, separately validated video/audio/subtitle stream extraction, and one decoder-validated PNG video preview; stream/timing/continuity/coverage/warning/tool/artifact evidence is persisted. | FFmpeg goals are unavailable when either tool is absent. Normalization remuxes without transcoding; it cannot recreate missing frames/samples. Preview is one frame, not recovered video. |
| External archives: 7z, RAR | Signature detection, bounded `7z` listing, conditional contained member extraction, and encryption/solid/multivolume evidence. | Requires a recorded 7-Zip-compatible tool. No native repair and no password guessing. Captured extraction output is bounded by the tool-output ceiling. |
| RTF | Inert partial text extraction and preview with object/active-content warnings. | Formatting and embedded-object fidelity are not recovered. |
| Legacy Office: DOC, XLS, PPT | OLE detection, macro/active-content signals, and conditional headless LibreOffice conversion to an inert PDF preview. Both `libreoffice` and Windows `soffice` command names are resolved. The exact PDF is natively validated before atomic publication. | Preview only: no editable Office recovery, macro retention, formula/animation proof, or password bypass. This machine lacks LibreOffice, so the live capability is unavailable here; adapter behavior is covered with controlled tool simulation. |

The checked-in [capability baseline](capabilities.generated.md) deliberately disables external tools for deterministic documentation. It therefore shows FFmpeg-, qpdf-, 7-Zip-, and LibreOffice-dependent goals as unavailable even when a particular workstation can provide them.

## Streaming And Memory Boundary

The public archive, package-document, PDF, TIFF/image, and media handlers no longer require a source-sized byte object for normal valid inputs:

- ZIP/TAR and package documents consume a seekable `FileByteSource` adapter and stream members to validators/publishers.
- XML package parts use pull parsing and bounded extracted-text accumulation.
- PDF uses chunked scanning with bounded overlap and tail buffers; qpdf/FFmpeg consume the exact immutable source path.
- TIFF/Pillow reads through the seekable source adapter; image outputs are produced as temporary files and then validated/streamed into atomic publication.
- Media native analyzers use bounded random reads; FFmpeg uses the source path directly unless a repaired prefix must be skipped, in which case bytes are streamed to a temporary input file.

This is not a claim that peak memory is constant for every codec. Pillow may decode full rasters/frames, XML text extraction has a defined cap, subprocesses have their own memory, and conservative corrupt-container reconstruction may require bounded materialization. The 16 MiB stored-ZIP regression verifies under `tracemalloc` that the native streaming validation path stays below a 12 MiB Python allocation peak and consumes zero materialized source bytes.

## Commands And Outcome Semantics

- `scan`: deterministic inventory and signatures only.
- `classify`: adds classification while preserving declared suffix, byte-zero signature, anywhere signature, and structural evidence separately.
- `recover`: executes selected recovery goals; `repair` is the only default.
- `benchmark`: runs the same recovery path plus main-process RSS sampling and optional labeled ground-truth evaluation.
- `report`: renders existing durable evidence without reopening source inputs.
- `capabilities`: emits runtime-resolved text, JSON, or Markdown support.

Every JSON manifest, JSONL attempt event, CSV row, and text report can distinguish all eight grades:

- `validated_original`
- `validated_normalized`
- `partial_content`
- `preview_only`
- `unavailable_dependency`
- `budget_exceeded`
- `cancelled`
- `failed`

Exit policies are selectable: `strict`, `partial-ok`, and `report-only`. Fatal configuration/runtime failures remain fatal under every policy. Exit codes are `0` accepted by policy, `1` partial/adverse, `2` fatal/cancelled/configuration failure, and `3` no results.

## Benchmark State

`benchmark --ground-truth <json>` now validates a versioned, path-contained, maximum-16-MiB label file and computes:

- classification, recovery, and fidelity accuracy;
- false-positive and false-negative rates from explicit recoverability labels;
- per-family/group aggregates and per-file comparisons;
- missing/extra files and optional source-hash identity mismatches;
- runtime, input/output/expansion, outcome/fidelity distribution, crashes, timeouts, budget stops, and cancellations;
- sampled main-process RSS baseline, peak, and peak-over-baseline, with method/sample metadata and the explicit boundary that child-process memory is not included.

Without ground truth, label-dependent metrics remain unavailable rather than fabricated. See [Benchmark ground truth](BENCHMARK-GROUND-TRUTH.md).

## Concrete Base For New Formats

A new type should be added through the existing contract rather than by modifying an all-purpose loop:

1. declare extension/signature evidence without promising recovery;
2. add license-safe valid and corrupt fixtures plus applicable mutation inventory;
3. implement `capabilities()`, read-only `inspect()`, bounded `plan()`, and `execute()` in one handler;
4. prefer streaming/random access and document any bounded materialization fallback;
5. publish only through `AtomicArtifactWriter` after exact-output validation;
6. persist typed format evidence, tool identity, transformations, and artifact relations;
7. expose unsupported/tool-absent goals as `none` or `unavailable_dependency`;
8. update generated capability documentation, indexes, security boundaries, and tests.

Plausible next families include GZIP/BZIP2/XZ, CPIO/CAB/ISO, JAR/APK/EPUB/CBZ, EML/MBOX, MSG/PST via an isolated adapter, SQLite/database salvage, and scientific/geospatial containers. Each needs its own format-specific validator and fidelity definition; recognizing a suffix is not enough.

## Remaining Gates And Highest-Value Improvements

1. Execute the clean-install Windows/Linux, Python 3.11-3.13, tool-present/tool-absent matrix on one exact committed SHA. This is the only open task in the current Spec Kit task list and requires separate commit/push/CI authorization.
2. Build a license-safe labeled real-world corpus with expected content/artifact hashes and publish support-tier thresholds. Synthetic fixtures prove contracts, not field recovery rates.
3. Add renderer-backed PDF page, image, font, metadata, and attachment recovery in a real isolation boundary; expand xref/object stream and incremental-update support.
4. Test qpdf, 7-Zip, LibreOffice, optional Pillow codecs, and the isolation wrapper with real installed tools on both operating systems. Current qpdf/7-Zip/LibreOffice tool-present tests are controlled simulations.
5. Measure whole process-tree memory for external tools. The current RSS sampler covers only the main Python process.
6. Add hostile-corpus fuzzing, decompression-bomb/raster limits below third-party decoders, dependency review, and an independent defensive security assessment.
7. Deepen semantic fidelity: Office styles/formulas/slide order, animated/multipage images, PDF renderer coverage, media packet/frame/sample coverage, metadata/ICC policy, and vendor RAW extraction.
8. Decide release readiness, signing, fixture licensing, distribution, and support policy independently. A green local suite does not authorize or prove a release.

## Repository And Authorization Notes

- `docs/OBSIDIAN.md` contains user-owned work and was preserved.
- Concurrent declared-video/embedded-JPEG classification work and its handoff were preserved.
- `.uncorrupter-workspace/`, `output/`, and `single-input/` are ignored local data, not implementation authority.
- `.agents/` and `.specify/` remain local-only workflow scaffolding.
- No staging, commit, push, pull request, workflow dispatch, package publication, release, deployment, or remote-setting change was performed or implied.

## Local AI workflow setup — 2026-09-05

A local project AI workflow defined completion behaviour, command routing and authorization reuse. It is superseded by the 2026-10-07 toolkit adoption below; `docs/agent-workflow.md` is now a compatibility index.

## Agent toolkit — 2026-10-07

The [portable toolkit](../.agent/README.md) establishes shared contracts, stable
repository-qualified identity, canonical skills and thin provider adapters.
The [adoption decision](decisions.md) covers ordinary scoped source workflow through
merge while preserving separate release/deployment gates and external protections.
This changes development guidance only. See the [handoff](../handoffs/2026-10-07-agent-toolkit.md)
for checks, isolated delivery and unavailable registry/provider evidence.
Since 2026-10-09 the Claude adapters for `release`, `deploy` and `publish` set
`disable-model-invocation: true`, so Claude loads them only on an explicit request.

## Source delivery of the 0.4.0 candidate — 2026-10-09

The previously uncommitted 0.4.0 candidate was committed on branch
`claude/v0.4.0-multiformat-recovery-20261009` and merged with `origin/main`
(toolkit PRs #12/#13). Conflicts kept the 0.4.0 product documentation and the
toolkit contract; `AGENTS.md` follows the toolkit and retains the GitHub Pro
memory block. Five files whose only local change was CRLF line endings
(`LICENSE`, `VERSIONS/`, legacy sources, one report), `specs/` and
`.codex/environments/` were left uncommitted. On a Linux host with Python 3.12 the
deterministic suite reported 154 passed and 1 skipped, and toolkit validation passed on
the committed tree. Remote CI evidence belongs to the pull request; this is not a release
or deployment.
