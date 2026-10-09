# Capabilities, Stabilization, And Roadmap

This document explains what File Uncorrupter `0.4.0` can do, how deeply each family is supported, what the stabilization work changed, and how additional formats can be added safely. The executable sources of truth are the registered handlers and `file-uncorrupter capabilities --format json`. The checked-in [generated baseline](capabilities.generated.md) is produced with external tools disabled and protected by a drift test.

## Capability Vocabulary

Recognizing a suffix or signature is not the same as recovering a file. Each operation has one of four levels:

- `validated`: executable fixtures verify the operation and its central safety/fidelity contract;
- `baseline`: a useful bounded operation exists, but validation depth is limited;
- `partial`: defensible structure or content may be recovered without full-file fidelity;
- `none`: the goal is unavailable and is rejected rather than silently substituted.

Runtime availability is resolved separately. An optional-tool operation may be present on one machine and `none` on another.

Attempt outcomes are also separate from capabilities:

- `validated_original`: the existing bytes passed the applicable validator;
- `validated_normalized`: a derived canonical artifact passed validation;
- `partial_content`: some defensible content was recovered, with loss/uncertainty;
- `preview_only`: an inspection derivative, not a recovered original;
- `unavailable_dependency`: the requested operation exists but its dependency does not;
- `budget_exceeded`: a declared resource ceiling stopped the operation;
- `cancelled`: cancellation was observed and recorded;
- `failed`: the operation could not produce a defensible artifact.

All eight grades are preserved in JSON, JSONL, CSV, and text reporting and participate in selectable exit policy.

## Runtime-Resolved Summary

| Family | Variants | Implemented operations | Conditional or deliberately limited |
| --- | --- | --- | --- |
| Text | TXT, Markdown, log, CSV, JSON, XML, HTML | Detect, inspect, validate, span-mapped extract, normalize, preview, partial repair/carve. | Very large text is bounded by materialization; semantic invention is forbidden. |
| Native archive | ZIP, TAR | Streaming inspect/validate/extract; conservative repair/carve. | Corrupt rebuild is bounded; no password cracking, normalize, or preview. |
| Package document | DOCX/DOCM, XLSX/XLSM, PPTX/PPTM, ODT/ODS/ODP | Streaming validate/inspect/extract; partial repair/preview/carve. | No native-application rendering proof or missing semantic reconstruction. |
| PDF | PDF | Streaming inspect/validate, partial extract/repair/carve; optional qpdf repair/validation. | No normalize/preview, OCR, renderer-backed page proof, or password bypass. |
| JPEG | JPEG | Validated repair; normalize/preview; partial carve/raw candidate. | Severe entropy reconstruction remains heuristic. |
| Image | PNG, GIF, BMP, WebP, TIFF, HEIF/AVIF, JP2, RAW/DNG | Native structure; partial repair/normalize/preview/carve where codec permits. | Extract is unavailable; optional codecs and frame/page fidelity vary. |
| Media | MP4/MOV, MKV/WebM, AVI, MPEG-TS/PS, FLV, ASF/WMV, WAV, MP3, FLAC, AAC, Ogg | Streaming native inspect, partial repair/carve. With FFmpeg+ffprobe: baseline copy-remux normalize, partial stream extract, partial one-frame preview. | Tool goals are `none` unless both tools exist; remux does not recreate missing media. |
| External archive | 7z, RAR | Detect/inspect and conditional bounded extraction. | Requires 7-Zip; no native repair; encryption/solid/multivolume remain explicit. |
| RTF | RTF | Partial inert text extract/preview. | Formatting and embedded objects are not recovered. |
| Legacy Office | DOC, XLS, PPT | OLE inspect and conditional LibreOffice-to-PDF preview. | Preview only; requires `libreoffice` or Windows `soffice`; no editable recovery. |

The tool-disabled baseline intentionally records conditional operations as unavailable. On the reviewed Windows machine, FFmpeg/ffprobe `8.1.2` make media normalize/extract/preview available; qpdf, 7-Zip, and LibreOffice are absent.

## Stabilization Completed

### Immutable Inputs And Streaming

- source identity, size, timestamp, and SHA-256 are captured without mutating the input;
- a read-only seekable `FileByteSource` adapter lets ZIP/TAR, package, PDF, TIFF/Pillow, and media paths consume the source without a source-sized `bytes` object;
- every read checks scan budget and source identity;
- archive/package members and output files stream through bounded atomic publishers;
- qpdf and FFmpeg consume the exact immutable source path directly when no prefix repair is needed;
- bounded complete-source materialization remains only for algorithms that genuinely need it, such as conservative corrupt-container reconstruction.

### Containment And Atomic Publication

- source symlinks/reparse points are rejected;
- unsafe root overlap is rejected before database creation;
- traversal, links, devices, and duplicate member names fail closed;
- output paths are contained under a deterministic per-file/per-goal namespace;
- existing artifacts are never silently overwritten;
- temporary outputs are validated, flushed, hashed, and atomically published where the filesystem permits.

### Resource And Process Control

- hierarchical budgets cover reads, materialization, candidates, tools, members, decompression, expansion, nesting, artifacts, output, and workers;
- bounded deterministic worker execution and cancellation are integrated into the coordinator;
- external tools use a single no-shell runner with minimal environment, temporary working directory, timeout, captured-output limit, process-tree cleanup, executable/version evidence, and optional fail-closed isolation wrapper;
- tool output artifacts have independent size and total-output limits.

### Evidence, Resume, And Reporting

- SQLite schema version 2 stores lifecycle, source identity, strategies, attempts, artifacts, validators, typed relations, tools, budgets, and events;
- per-file transactions preserve completed evidence after a later file fails;
- resume checks effective configuration and source identity and never overwrites prior outputs;
- deterministic JSONL events and JSON/CSV/text reports separate file status from outcome grade;
- every outcome grade and exit policy has exhaustive tests;
- two independent runs are compared after removing only run IDs/timestamps, including ordering, selected artifact identity, strategy order, and hashes.

### Benchmarking And Coverage

- a versioned ground-truth JSON schema labels family, recoverability, acceptable grades, and optional source hash by safe relative path;
- classification, recovery, fidelity, false-positive, and false-negative rates are computed globally and per family/group;
- main-process RSS is sampled during recovery with baseline, peak, delta, method, interval, and sample count;
- the benchmark explicitly states that child-process memory is not included;
- valid/wrong-suffix/resource/corruption variants cover every public format variant as applicable;
- a 16 MiB stored-ZIP regression verifies zero source materialization and a sub-12-MiB traced Python allocation peak on the streaming path.

## Format Detail And Improvement Paths

### Text, TXT, Markdown, And Structured Text

Implemented:

- UTF-8, UTF-16 LE/BE, and UTF-32 LE/BE BOM recognition;
- Windows-1252 and ISO-8859-1 fallback evidence;
- exact, replacement, and skipped-binary byte spans plus output/source offset maps;
- JSON/XML validity; CSV dialect/shape; HTML tag/link/active-content; Markdown heading/link/fence diagnostics;
- inert extraction and separate UTF-8/newline normalization.

Best next work:

- incremental decoding for multi-gigabyte logs beyond the current materialization ceiling;
- YAML/TOML/INI handlers using safe parsers;
- labeled multilingual encoding benchmarks;
- redaction-aware, explicitly opted-in excerpt reporting.

### ZIP, TAR, 7z, RAR, And More Archives

Implemented:

- streaming ZIP central-directory validation and member CRC/size checking;
- local-header salvage when reconstruction is unambiguous;
- streaming TAR checksum scan, member extraction, and later-member resynchronization;
- global member, member-size, decompression, expansion, nesting, artifact, and output limits;
- 7z/RAR tool-conditional listing/extraction with solid, volume, and encryption evidence.

Best next work:

- ZIP64/data-descriptor and sparse/PAX/GNU TAR corpus depth;
- recursive archive coordination under one run-wide decompression budget;
- streamed external-tool extraction without captured-member memory;
- native metadata-only 7z/RAR readers;
- GZIP/BZIP2/XZ, CPIO, CAB, ISO/DMG, JAR/APK, EPUB, and CBZ handlers.

### Modern Documents

Implemented:

- Open XML/OpenDocument type detection independent of suffix;
- streaming validation of content types, manifests, root relationships, and required main parts;
- text, worksheet, slide, media, and embedding classification/extraction;
- macro, external relationship, active XML, and embedded-object warnings;
- conservative package rebuild from defensible parts only.

Best next work:

- shared strings, formula/value pairing, slide order, styles, notes, comments, footnotes, and tracked-change fidelity;
- renderer-backed comparison inside a genuine sandbox;
- encrypted package metadata classification without password guessing;
- EPUB package specialization;
- EML/MBOX, then MSG/PST only through maintained isolated adapters.

### Legacy DOC, XLS, PPT, And RTF

Implemented:

- OLE/CFB and macro/active-content signals;
- RTF inert text extraction;
- bounded headless LibreOffice preview conversion using a private profile, safe/headless flags, timeout/cancellation, output cap, native PDF validation, and atomic publication;
- cross-platform resolution of `libreoffice` and `soffice`.

Best next work:

- real tool-present Windows/Linux corpus validation;
- OLE directory/stream parsing and encryption classification;
- Word text, Excel values/formulas, and PowerPoint slide text extraction independent of LibreOffice;
- page/sheet/slide coverage comparison. Editable reconstruction should remain a separate, much stronger claim.

### PDF

Implemented:

- incremental scans for headers, explicit object offsets, streams, pages, encryption, embedded files/actions, classic xref/trailer/startxref/EOF;
- conservative prefix removal, EOF append, and classic-xref reconstruction;
- bounded partial literal-string text extraction;
- qpdf repair and `--check` validation followed by native validation and exact-hash atomic publication;
- explicit large-source fallback diagnostics instead of unbounded allocation.

Best next work:

- xref/object streams, hybrid references, incremental updates, linearized PDFs, and damaged page-tree graph recovery;
- separately validated page text, images, fonts, metadata, annotations, and attachments;
- renderer comparison, page coverage, and OCR as separately labeled derivatives;
- encrypted metadata inventory without password bypass.

### JPEG And Other Images

Implemented:

- JPEG bounded candidate generation, structural validation, Pillow decoding, deterministic selection, and exact artifact publication;
- PNG chunk/CRC/order analysis; GIF table/block/frame/trailer analysis; BMP DIB/pixel-offset analysis; WebP RIFF/chunk/padding analysis; TIFF byte-order/IFD/range/cycle analysis;
- seekable decoder input and temporary-file output validation/publication;
- explicit animation/multipage and first-frame/page fidelity grades;
- runtime codec boundaries for HEIF/AVIF, JPEG 2000, and RAW/DNG.

Best next work:

- pixel-count/decompression-bomb budgets independent of Pillow defaults;
- frame/page artifact relations for every multipage output;
- EXIF/XMP/ICC/metadata retention policy;
- native HEIF item/property and JP2 codestream recovery;
- vendor RAW preview extraction and a maintained codec matrix;
- pixel/perceptual benchmarks against expected images.

### Video And Audio

Implemented:

- native MP4/MOV box and `moov`/fragment evidence;
- EBML, RIFF, MPEG-TS continuity, MPEG-PS, FLV, ASF, WAV, MP3, FLAC, AAC, and Ogg structure evidence;
- streaming prefix removal and RIFF-size repair where derivable;
- FFmpeg copy-remux normalization to MKV/MKA, one output per supported video/audio/subtitle stream, and one PNG video preview;
- ffprobe validation of exact temporary artifacts before streamed atomic publication;
- source/output stream inventory, timing/duration/frame evidence, continuity warnings, decoded coverage, hashes, tool runs, artifact relations, and fidelity grades.

Best next work:

- packet/frame/sample-level decoded coverage rather than stream-type preservation alone;
- audio waveform/spectrogram preview as separately labeled derivatives;
- optional user-selected transcoding profile, never confused with lossless recovery;
- deeper fragmented MP4/index reconstruction and Matroska cue/seekhead recovery;
- malformed timestamp and codec-specific corpora on both operating systems;
- child-process CPU/RSS/IO sampling.

## Other Format Possibilities

The handler base is suitable for more than office/media files, but each addition needs a validator, a fidelity model, budgets, hostile fixtures, and truthful unavailable states.

| Candidate family | Sensible first capability | Main risk/boundary |
| --- | --- | --- |
| GZIP/BZIP2/XZ | Stream validation and one contained member extraction. | Expansion bombs, concatenated streams, missing trailer checksums. |
| JAR/APK/EPUB/CBZ | ZIP specialization plus required manifest/content checks. | Active code/signatures, path attacks, misleading generic ZIP claims. |
| EML/MBOX | Header/MIME inspection and inert attachment/text extraction. | Encodings, nested MIME, active HTML, personal data. |
| MSG/PST/OST | Metadata-first optional isolated adapter. | Proprietary complexity, huge stores, privacy, external parser risk. |
| SQLite | Header/page inventory and conservative table/index salvage. | Transaction/WAL consistency, false rows, semantic integrity. |
| Other databases | Vendor/tool-specific export through explicit adapters. | Credentials, server mutation, proprietary formats, very large data. |
| ISO/UDF/DMG | Read-only filesystem inventory and contained extraction. | Nested filesystems, links/devices, compression/encryption. |
| Scientific/geospatial | Metadata and chunk/table extraction for HDF5/NetCDF/FITS/GeoTIFF. | Huge arrays, external links, datatype/coordinate fidelity. |
| Source/code bundles | Encoding/newline recovery and syntax diagnostics. | Never execute recovered code; dependency secrets and generated data. |

## Deliberate Non-Capabilities

File Uncorrupter does not:

- recover bytes that are absent or infer unknown original content;
- crack passwords, defeat encryption, or bypass rights/access controls;
- execute macros, scripts, HTML, links, OLE objects, archive members, or recovered binaries;
- claim editable Office recovery from a PDF preview;
- claim a single image frame is a recovered animation/video;
- claim a successful remux repaired missing encoded media;
- claim tool availability from installation alone without exact-output validation;
- overwrite the source or silently replace an existing artifact;
- treat green local tests, a workflow definition, a version, or a build as a release/deployment.

## Prioritized Roadmap

1. Run the existing exact-commit CI matrix after explicit commit/push authorization; correlate every check to the SHA.
2. Build and license a labeled real-world corpus with artifact/content hashes and support-tier thresholds.
3. Add renderer-backed PDF and Office coverage inside an actual isolation boundary.
4. Run real qpdf/7-Zip/LibreOffice/optional-codec matrices on Windows and Linux.
5. Add process-tree memory/CPU/IO measurement, not only main-process RSS.
6. Deepen per-format semantic fidelity and large-file incremental text/corrupt-container algorithms.
7. Add hostile-corpus fuzzing, dependency review, and independent defensive security assessment.
8. Decide publication, signing, distribution, support, and compatibility policy separately.

See [Current state](current-state.md), [Benchmark ground truth](BENCHMARK-GROUND-TRUTH.md), [Security](security/SECURITY.md), and [Verification](testing/VERIFICATION.md) for the operational boundaries behind this roadmap.
