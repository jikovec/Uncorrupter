# Uncorrupter Master Research and Architecture Blueprint

## Current-state diagnosis and project analysis

**What follows treats the uploaded materials as primary evidence** (the monolithic `a.py`, the modular repo in `Uncorrupter.zip`, and the run evidence in `recover_summary.json` plus the accompanying reports). Where an exact behaviour is inferred from the run evidence rather than explicitly visible in the uploaded source, it is marked as such.

**1. Executive Diagnosis**

**Project state (evidence-grounded).** The current system has already discovered the right “macro shape” for a serious recovery platform: ingest → triage/classify → generate candidates → try decoders → score outcomes → persist evidence and report. `a.py` implements this as a single script with aggressive candidate carving and per-file diagnostics. fileciteturn3file0 The `Uncorrupter.zip` repository evolves it into a modular CLI framework with a persistent run database, a recovery pipeline, an engine registry, and tests (observed directly from the extracted repository contents).

**What v1 is doing right.** `a.py` explicitly recognises that most failures are candidate-generation failures, not “decoder failures”, and it invests in marker diagnostics and aggressive carving rather than superficial “try to open the file” attempts. fileciteturn3file0 It also toggles truncated JPEG loading in Pillow, matching Pillow’s own documentation that truncated JPEG loading is disabled by default unless explicitly overridden. citeturn2search17

**What v2 is doing right.** The modular repo establishes the correct long-term direction: (a) a pipeline with repeatable runs, (b) explicit classification labels (currently JPEG-focused), (c) a scoring function that can incorporate classification-specific priors, and (d) a SQLite-backed evidence store enabling experiment tracking and reporting (observed directly from the extracted repository).

**The hard reality shown by run evidence.** The measured recovery rate is extremely low: `11/2328` recovered (≈0.47%). fileciteturn5file0 Nearly everything is declared JPEG (`2321/2328`), and almost nothing has a valid signature at byte 0 (`unknown: 2326`, `jpeg: 2`). fileciteturn5file0 That combination strongly suggests a corruption model dominated by **missing/overwritten leading bytes** and/or **prefix garbage / misalignment**, rather than “mild bit flips” in-place. It also means extension-only workflows (or byte-0 signature-only workflows) are structurally doomed without deeper carving and reconstruction.

**Why the recovery rate is still low (most load-bearing causes).**

1) **Missing SOI/header dominates.** The run summary explicitly reports `1152` failed JPEGs with internal JPEG structure but no SOI. fileciteturn5file0 If the SOI and early header segments are gone, “prepend SOI” alone is rarely sufficient; a decoder often needs a coherent header set (SOF, DQT, DHT, SOS ordering constraints) rather than a token SOI.

2) **Missing Huffman tables is common.** `248` JPEGs reportedly contain SOS but no DHT, and the run summary explicitly points to “MJPEG-style DHT repair” as relevant. fileciteturn5file0 This aligns with real-world practice: certain MJPEG-like streams rely on default Huffman tables rather than embedding DHT per frame (this is widely discussed in JPEG tooling communities), and repair often means injecting a known-good DHT before SOS.

3) **Strategy coverage is not yet “format-deep”.** The winner strategies in the run evidence are almost entirely `jpeg_rebuilt_header_from_segments` (10) and a single `jpeg_soi_to_end` (1). fileciteturn5file0 This is a strong signal that *the few successes came from header reconstruction*, not from basic SOI/EOI carving. In other words: the pipeline is currently missing whole families of “repair-by-reconstruction” strategies that are essential when the beginning of the file is destroyed.

4) **Evidence suggests extension-trusting constrained exploration.** The run summary says all files used `extension_trusted` as the policy. fileciteturn5file0 `a.py` explicitly implements an extension-first policy (recover only as the extension’s format unless no extension and no byte-0 header). fileciteturn3file0 That’s defensible for a dataset where extensions are reliable, but it becomes a hard ceiling for broader “any media blob” recovery.

**Main technical bottlenecks (ranked).**

- **Bottleneck A: Candidate generation is not yet capable of reassembling fragmented or partially displaced structures** (especially for JPEG/ISOBMFF/EBML families). This is consistent with forensic literature: basic carving works for contiguous files but struggles with fragmentation; practical systems need “object validation” and smarter reassembly. citeturn9search2turn9search6
- **Bottleneck B: Format-specific reconstruction layers are missing for most formats** (beyond heuristic windowing).
- **Bottleneck C: Decoder adapter strategy is underpowered for video** (because video isn’t first-class yet, and because effective video salvage often requires container/index rebuild, stream resync, and frame-level extraction paths rather than a single “decode-or-fail”).

**What changes because the target is now image + video.** Video recovery makes the system fundamentally more “multi-output”:

- A single input can yield: a playable remux, multiple partial clips, streams, and thousands of recovered frames.
- Repair is often **container/index reconstruction** (e.g., MP4 missing `moov`, AVI missing `idx1`, Matroska cue placement) rather than “fix compressed pixels”.
- Success is not binary; a partially playable segment or a set of recovered keyframes is still valuable, and must be scored and reported differently from still images.

**2. Current Project Analysis**

### Deep analysis of `a.py` (v1)

**Declared design intent.** `a.py` is explicitly an “aggressive damaged-image recovery” script that treats extension as authoritative, focuses on candidate generation, emits detailed logs, and optionally uses FFmpeg as a secondary decoder. fileciteturn3file0

**Key architectural behaviours (as implemented).**

- **Extension-first selection policy.** If an input has `.jpg/.png/.gif/...` it is recovered only as that kind (unless later fallback is enabled by failing primary kinds; in the run evidence, fallback wasn’t used). fileciteturn3file0
- **Multi-format marker diagnostics.** The script counts markers (JPEG SOI/EOI/SOS/DQT/DHT/SOF, PNG signature/IHDR/IDAT/IEND, etc.) and uses that to suggest next strategy families. fileciteturn3file2
- **Candidate model.** A candidate is essentially a byte-range slice plus optional prepend/append bytes with a priority, and candidates are generated per format. fileciteturn2file0
- **Decoder adapters (image-only).** The script probes with Pillow, optionally probes with FFmpeg, and writes outputs in the “intended” format, normalising image modes. fileciteturn2file5turn2file4
- **Success selection heuristic.** Best candidate is chosen by “largest decoded area” among successful probes. fileciteturn2file5

**Strengths (why it mattered).** The design implicitly applies a forensic principle: you can generate many hypotheses and use decoder validation as an oracle. This parallels “object validation” from forensic carving research: candidate sequences are tested for validity of the target object type, not merely for presence of magic bytes. citeturn9search2turn9search6

**Limits (why it stalls).**

- For JPEG, the hard cases are not “find SOI” but “reconstruct a coherent header + Huffman/quant tables + salvage scan data”. A token SOI prepend rarely creates a valid parse tree when DQT/DHT/SOF are missing or inconsistent.
- For PNG, strict zlib stream integrity means internal corruption often kills decompression; PNG’s robustness is about detection (CRC), not graceful partial decode. citeturn3search0turn3search16turn3search13
- The candidate model is too limited for serious video: video recovery often needs **fragment graphs**, not “one contiguous slice”.
- Results storage is file-based reports (CSV/JSON), which is good for a script but weak for long-term experiment tracking at scale.

### Deep analysis of `Uncorrupter.zip` (v2)

**Observed structure (from extracting the repo).** The repo includes:

- A CLI (`file-uncorrupter`) with commands for scan/classify/recover/report.
- A pipeline object orchestrating scan → classify → recover.
- A JPEG engine (`jpeg-v1`) with candidate generation and classification-aware scoring.
- A SQLite database storing runs/files/attempts/outputs.
- Unit tests for classification, database writes, and recovery behaviours.

**What it improves over `a.py`.**

- **Persistent experiment tracking.** The SQLite schema and run IDs enable longitudinal benchmarking (essential for an “aggressive experimentation” roadmap).
- **Clear module boundaries.** Intake, classification, engines, decoders, scoring, reporting are separated, which is a prerequisite for multi-format expansion and video support.
- **Scoring is extensible.** It already supports classification-conditioned scoring, moving towards a system that can prioritise strategies by failure cluster.

**What it still lacks relative to the new target.**

- **Media-generic top level**: currently the engine registry is effectively JPEG-only.
- **Candidate representation** still assumes “single blob candidate”; video needs multi-stream, multi-fragment representations.
- **Format coverage**: the expanded image families (HEIF/AVIF/JPEG2000/RAW) and video families are not present yet.
- **Deep repair tooling integration**: tools like MP4 atom editors and TS resyncers (Bento4/TSDuck/etc.) are not integrated.

**Direct comparison: v1 vs v2**

- v1 (`a.py`) excels at breadth of image formats and rapid hypothesis generation but is monolithic and hard to evolve systematically. fileciteturn3file0
- v2 excels at system architecture (repeatability, evidence store, pipeline), but its recovery intelligence is still narrow and needs major format- and media-generic refactoring.

**What should be preserved.**

- From v2: pipeline + run DB + modular engine registry + tests (the evolution backbone).
- From v1: broad marker diagnostics and the general idea of “candidate families per format”.

**What should be discarded or rewritten.**

- Discard the “single script as product” model.
- Rewrite the candidate model to support: (a) multi-fragment assemblies, (b) synthetic header construction as first-class, (c) streaming candidates for huge files.
- Rewrite classification to be media-generic and include video/container families.

**Which existing parts are too image-specific and must become media-generic.**

- Classification labels limited to JPEG patterns.
- “Decoder = image library probe” assumptions; videos need multi-step demux/decode and fallback to frame extraction.
- Output model: single recovered file; videos can yield multiple artifacts.

**3. External Research and Prior Art (high-signal synthesis)**

This section focuses on **mechanisms** that materially affect recoverability, not superficial tool lists.

### File carving and forensic object validation

**Signature-based carving as baseline (what it provides).**

- entity["organization","PhotoRec","file carver by cgsecurity"] is explicitly described as a signature-based file recovery utility (“file carver”), able to recover files even from corrupted filesystems, but without original filenames/structure. citeturn0search1turn0search15
- entity["organization","Foremost","file carving utility"] recovers based on headers/footers/internal structures (“data carving”). citeturn0search16turn0search2

**Critical limitation (must shape Uncorrupter’s architecture).** Classic carving assumes contiguous data; fragmentation breaks naive header→footer extraction. Forensic literature is explicit that fragmentation reassembly is a core unsolved problem for basic carvers, motivating object validation and smarter methods. citeturn9search6turn9search2

**Object validation as a design pillar.** Garfinkel’s DFRWS work formalises “object validation” as determining whether sequences of bytes represent valid target objects, improving carving especially in the presence of fragmentation and noise. citeturn9search2turn9search6  
**Adopt for Uncorrupter:** treat decoders/parsers/scorers as validation oracles in a systematic pipeline.

**Fragmentation-point detection: JPEG-specific advances.** Modern work on deterministic JPEG fragmentation point detection suggests you can identify valid continuation blocks at bit-level with high accuracy, which is directly relevant if your corruption involves internal truncation/reordering. citeturn2search12turn2search8  
**Adopt for Uncorrupter:** a “fragment graph” strategy for JPEG that can propose concatenations and validate them via decoder success.

### Damaged image repair and decoder-assisted salvage

**JPEG: what matters in practice.**

- JPEG structure is marker-segment driven; Huffman tables are defined via DHT segments. citeturn2search1turn2search5
- Pillow documents that truncated JPEG loading is not allowed by default and must be explicitly enabled. citeturn2search17

**Mechanism to borrow: “missing DHT / MJPEG-style default Huffman”.** The run evidence explicitly flags SOS-without-DHT cases and points to MJPEG-style DHT repair. fileciteturn5file0 The practical takeaway: Uncorrupter needs a first-class strategy family for **injecting known-good Huffman tables** (and, when needed, quant tables) before SOS, and then validating.

**PNG: robust detection, weak tolerance.**

- PNG is defined as a signature followed by chunks; a valid PNG must contain IHDR, one or more IDAT, and IEND. citeturn3search0turn3search16
- Tools like `pngcheck` emphasise CRC and structural conformance checking, reinforcing that “repair” often means fixing chunk structure and CRCs, but decompression corruption is frequently fatal. citeturn3search13turn3search1

**WebP: RIFF container constraints.**

- WebP is RIFF-based and supports lossy/lossless/extended variants; the container structure and chunk ordering matter for renderability. citeturn3search2turn3search6turn3search18  
**Adopt:** For RIFF-like formats, implement “size-field repair” + chunk scanning + subtype-aware validation (VP8/VP8L/VP8X).

**TIFF: IFD/offset integrity is everything.**

- TIFF is IFD-driven; strip offsets and tag structures define where pixel data lives. citeturn4search0turn4search8  
**Adopt:** Repair often means rebuilding/repairing IFD chains and strip/tile offset tables, not decoding compressed pixels first.

**Modern still-image containers (HEIF/AVIF).**

- entity["organization","libheif","heif avif codec library"] is a decoder/encoder for HEIF and AVIF; HEIC typically uses HEVC, AVIF uses AV1. citeturn7search0
- The AVIF specification explicitly states that AVIF stores AV1 images in HEIF, which is based on ISOBMFF. citeturn7search1turn7search5turn7search9  
**Adopt:** Treat HEIC/AVIF as “ISOBMFF + codec payload”, so many MP4/MOV repair mechanisms apply.

**JPEG 2000 and RAW-family support.**

- JPEG 2000 decoding typically relies on libraries like OpenJPEG; codestream parsing is marker-driven (analogous to JPEG but different structure). citeturn7search10turn7search2
- entity["organization","LibRaw","raw image decoding library"] supports many RAW formats and is designed for embedding in converters/analyzers. citeturn7search3turn7search7  
**Adopt:** For RAW, start with container-level identification (many are TIFF-derived) and rely on LibRaw for decode attempts, while keeping a “metadata salvage” path even when pixels fail.

### Damaged video and container repair

Video repair is typically “container metadata reconstruction + tolerant decode”, not pixel repair.

**MP4/MOV (ISOBMFF): moov/index reconstruction.**

- Bento4 explicitly models MP4 as a tree of atoms/boxes with structural inspection tools. citeturn5search5turn5search1
- entity["organization","untrunc","mp4 repair tool"] repairs truncated MP4/MOV by leveraging a similar, not-broken reference file. citeturn0search0turn0search6turn0search14turn5search0  
**Adopt:** Provide a “reference-assisted” MP4 repair mode (and automate reference selection from a local corpus when possible).

**AVI: index/header rebuild.** DivFix++ describes rebuilding headers and generating an index table by scanning chunks, then merging the generated index at `idx1` or file end. citeturn6search4turn6search16  
**Adopt:** An AVI repair strategy family should explicitly rebuild `idx1` and normalise RIFF sizes, then validate via tolerant demux/decode.

**Matroska (MKV/WEBM): EBML structure and cues.** Matroska ordering guidance exists to support better playback/seeking. citeturn6search1turn6search5turn6search13  
**Adopt:** Build a “cluster scan + cues rebuild” strategy, and provide a “remux via tolerant demuxer” path as a fallback.

**MPEG Transport Stream: resynchronisation and packet carving.**

- MPEG-TS uses fixed 188-byte packets with a sync byte; resync often means scanning until sync is found again. citeturn5search11turn5search15turn5search7
- TSDuck explicitly provides a `tsresync` utility to extract packets and recreate conformant 188-byte TS streams. citeturn5search3  
**Adopt:** TS recovery should be a first-class, high-success strategy: resync → extract programs/streams → decode.

**FLV and ASF/WMV.**

- The FLV spec defines tag structure and stream constraints (typically ≤1 audio and ≤1 video stream). citeturn6search2turn6search14
- Microsoft’s ASF overview describes files as “objects” with required Header and Data objects and an optional Index object. citeturn6search3turn6search7  
**Adopt:** Provide container parsers that can salvage split/partial tag/object sequences, plus an extraction path that yields elementary streams or decoded frames when container repair fails.

### Decoder-assisted salvage via FFmpeg

FFmpeg is not just a transcoder; it exposes explicit knobs for “decode despite errors”:

- `err_detect` flags include `ignore_err` to continue decoding despite errors (useful for analysis rather than perfect playback). citeturn1search1turn1search0
- `-fflags discardcorrupt` discards corrupted packets at the demuxer/format layer. citeturn8search15  
**Adopt:** Uncorrupter must institutionalise “decoder configurations as strategies”, not “one FFmpeg call”.

### Forensic workflows, evidence integrity, and tool testing

- NIST SP 800-86 emphasises forensic handling and evidence integrity as part of incident response and investigation workflows. citeturn9search0turn9search4
- NIST’s CFTT programme exists because forensic tools require reliable, repeatable testing methodologies. citeturn9search9turn9search1  
**Adopt:** Uncorrupter must treat itself like a forensic tool: deterministic runs, recorded versions/configs, reproducible benchmarks, regression locking.

**4. Decision Matrix of Existing Approaches (explicit “borrow/avoid” list)**

The table below focuses on items that directly inform Uncorrupter’s future architecture and strategy catalogue.

| Item | Category | Problem addressed | Strengths | Weaknesses | Relevance to Uncorrupter | Borrow? | Exact mechanisms to borrow | Avoid copying | Where it belongs |
|---|---|---|---|---|---|---|---|---|---|
| PhotoRec citeturn0search1turn0search15 | File carving | Recover files from raw/damaged media via signatures | Works without filesystem; supports many file types; robust in practice | Loses filenames/structure; struggles with fragmentation; limited “repair” beyond carving | High for “signature hunting anywhere in blob” | Yes | Signature scanning pipelines; carving output separation; “don’t write to source” operational posture | Treating “header match = recovery”; lack of deep validation/repair | Baseline architecture (triage + signature index) |
| Foremost citeturn0search16turn0search2 | File carving | Header/footer/internal structure carving | Configurable signatures; simple carving model | Fragmentation limitations; can overcarve/false-positive | Medium | Adapt | Config-driven signature definitions; carve window constraints | Overreliance on footer-based termination | Baseline + benchmarking comparison |
| Garfinkel object validation citeturn9search2turn9search6 | Forensic methodology | Validate candidate byte sequences as real objects | Formalises decoding/validation as oracle; improves carving quality | Not a turnkey implementation; requires validators per format | Very high | Yes | “Candidate → validator → confidence” pipeline; store validation evidence | Manual-only validation; no scoring automation | Baseline architecture (candidate scoring + evidence) |
| Deterministic JPEG fragmentation-point work citeturn2search12turn2search8 | JPEG reassembly | Detect continuation points/fragmentation boundaries | Directly targets fragmented/truncated JPEG recovery | More complex; may be compute-heavy | High if corruption includes internal truncation/fragmentation | Yes (aggressive modes) | Fragment-graph proposals; bit-level continuation tests; near-boundary search | Forcing it as baseline for all JPEGs (expensive); claiming it solves all | Aggressive recovery mode + research/benchmarking |
| ITU-T T.81 / JPEG structure citeturn2search1 | Format spec | Defines DHT/DQT/SOF/SOS semantics | Primary reference for correct parsing/rebuild | Dense; not implementation-specific | Foundational | Yes | Marker parsing rules; segment legality checks; reconstruct header in valid order | “Spec purity” as goal; practical decoders accept noncompliance | Baseline validator + repair-core |
| Pillow truncated JPEG behaviour citeturn2search17 | Decoder behaviour | Control over truncated decode | Quick check/normalise; widely used | Not tuned for salvage; limited diagnostics | Medium | Adapt | Use as one decoder oracle and for normalised output | Treating Pillow as “the” decoder; missing multi-decoder cross-check | Baseline decode adapter (images) |
| FFmpeg error-tolerant decode knobs citeturn1search1turn8search15turn1search0 | Decoder-assisted salvage | Decode despite container/bitstream errors | Supports huge range; explicit ignore/discard flags; can output frames | CLI invocation overhead; success varies by codec | Essential for video | Yes | Parameterised decoder strategies; frame extraction as fallback | One fixed FFmpeg command; assuming “playable output” is always possible | Baseline video adapter + aggressive modes |
| untrunc citeturn0search0turn0search6 | Container repair | Repair truncated MP4/MOV missing `moov` using reference | Works in common “power cut” cases; proven tool | Needs similar reference file; uncertain outcomes | High | Yes (optional) | Reference-assisted moov rebuild; automate reference selection from local corpus | Making it the only MP4 strategy; ignoring reference-less cases | Aggressive mode + corpus tooling |
| Bento4 MP4 tools citeturn5search5turn5search1 | Container parsing/editing | Inspect/edit MP4 box structure | Precise box tooling; useful for diagnostics and targeted edits | Not a “repair everything” system by itself | High | Yes | Use for structural diagnostics; box-level extraction/modification steps | Overdependence on one toolkit; ignoring FFmpeg demux tolerance | Baseline diagnostics + plugin strategy |
| DivFix++ AVI repair description citeturn6search4turn6search16 | Container repair | Rebuild AVI headers/index | Explicitly describes scanning chunks and rebuilding index | Limited to AVI; implementation specifics | Medium | Adapt | “Scan chunk IDs → rebuild index” concept; validate via remux/decode | GUI-centric workflow; opaque heuristics | Baseline AVI repair engine |
| Matroska spec + ordering citeturn6search5turn6search1 | Container spec | EBML structure, ordering, cues | Standards-track spec; clarifies element ordering guidance | Complex; seeking issues vary | High | Yes | “Cluster scan → cues rebuild”; element ordering checks for validation | Assuming cues must be present for salvage; some players tolerate | Baseline MKV/WEBM engine |
| TSDuck `tsresync` citeturn5search3 | Stream repair | Resynchronise and fix TS packetisation | Purpose-built for TS; high success class | TS-specific; needs tooling integration | High for TS | Yes | TS packet carving/resync; downstream demux/decode | Treating TS as just another file; ignoring its structure | Baseline TS engine |

## Problem model and requirements

**5. Problem Model (rigorous definitions aligned to this domain)**

### Corruption classes that matter

Uncorrupter must model corruption as multi-layer phenomena:

- **Binary-layer corruption:** inserted garbage prefixes, missing prefixes, overwritten regions, truncation, block loss, repeated blocks, byte shifts, random bit flips, and fragmentation/reordering (common in partial copies or damaged storage).
- **Structural-layer corruption:** missing headers/footers, broken length fields, invalid offsets (TIFF strips/tiles), broken chunk tables (RIFF/AVI), missing indexes (MP4 `moov`, AVI `idx1`, Matroska cues), inconsistent metadata sections.
- **Compressed-stream-layer corruption:** entropy-coded scan damage (JPEG), zlib stream damage (PNG), codec NAL unit damage (H.264/H.265), GOP breakage, missing SPS/PPS/VPS, corrupted packet boundaries.
- **Render/output-layer corruption:** partial decode, wrong colours due to wrong tables, block artefacts, missing rows/frames, timestamp chaos, audio/video drift.

### What “recovery” means

**Recovery = producing one or more output artifacts whose visual content is plausibly derived from the input blob and is maximally useful under the corruption constraints.**

For still images, recovery has levels:

- **Level I (strict):** decodes without errors/warnings and renders fully.
- **Level II (tolerant):** decodes with warnings, partial truncation handling, or visible artefacts, but yields substantial readable content.
- **Level III (salvage):** yields partial regions (e.g., top N rows, partial MCUs) or a best-effort reconstruction with known incorrect tables, but content is recognisable.

For videos, recovery has more distinct success modes:

- **Playable container output:** the output plays in at least one mainstream player through at least some duration.
- **Seekable output / index rebuilt:** scrubbing/seeking works across recovered ranges.
- **Clip salvage:** one or more contiguous playable segments extracted from a broken file.
- **Frame salvage:** extracted decoded frames (especially keyframes) in correct or approximate order, even if no playable continuous video is produced.
- **Stream salvage:** extracted elementary streams (H.264/H.265/AAC) suitable for later remux.

### False positives vs meaningless output

- **False positive:** decoder “succeeds” but output does not plausibly originate from the input’s embedded media (e.g., accidental decode of random bytes yielding noise or a tiny bogus frame). False positives are expected in aggressive carving and must be controlled via validation/scoring.
- **Meaningless output:** technically decodable but not useful (e.g., 1×1 images, single-colour frames, corrupted thumbnail only, or a video with 0.2 seconds and no frames).

### How to judge success without ground truth

Without a known-good original, Uncorrupter must rely on **multi-signal scoring**:

- Structural plausibility (valid marker/chunk/order; sane dimensions/durations).
- Decoder diagnostics profile (warnings vs hard errors; error locality).
- Output magnitude (area, duration, frame count).
- Content heuristics (entropy, edge density, variance; not perfect but useful).
- Cross-decoder agreement (two decoders produce consistent metadata → higher confidence).

This directly maps to the “object validation” idea in carving research: validity signals are aggregated to decide which candidate outputs represent real objects. citeturn9search2turn9search6

**6. Requirements (complete set, grouped for implementation clarity)**

### Functional requirements

The system must:

- Ingest individual files and directories; support recursive batch operations; support “all files” scanning (not extension-limited).
- Compute and persist strong hashes (SHA-256) for input integrity and deduplication.
- Detect likely media families via byte-0 signatures **and** internal signature scanning (because byte-0 is often destroyed per run evidence). fileciteturn5file0
- Perform format-specific triage and classification, producing an explainable label set and confidence.
- Generate recovery candidates using a plugin strategy system with per-family engines.
- Run multi-decoder validation attempts per candidate (at least: one strict parser/validator; one tolerant decoder).
- Produce multiple outputs per input where appropriate (especially for video): repaired containers, clips, frame sets, thumbnails, and raw artifacts.
- Rank candidates and outputs; store the “best” plus optionally store top-K.
- Generate human-readable reports and machine-readable JSON/CSV/Parquet exports.

### Non-functional requirements

The system must:

- Be offline-first: no required online services; no mandatory network calls.
- Be deterministic where possible: record versions, configs, strategy sets, seeds.
- Scale to large files (multi-GB videos) without requiring full RAM loads (stream/mmap design).
- Be robust under pathological inputs (fuzz-like corruption); avoid crashing; enforce timeouts and memory limits per decode attempt.

### Observability requirements

- Structured logging per run, per file, per candidate, per decoder attempt.
- Persist decoder stderr/stdout snippets (bounded) and structured error codes.
- Persist marker/signature statistics and classification evidence.

### Experiment/research requirements

- Allow A/B testing of strategy sets.
- Track per-strategy success rates by file family and by classification cluster.
- Enable “replay this run exactly” functionality.

### Reproducibility requirements

- Each run must store: engine version, strategy registry version, decoder versions, OS info, configuration snapshot, and corpus references.
- Outputs must be content-addressed and immutable once written (or versioned), enabling regression comparisons.

### Corpus/fixture requirements

- Support corpora containing: (a) real corrupted files, (b) synthetic corruptions with known ground truth, (c) reference files for tools like untrunc. citeturn0search0turn0search6
- Maintain cluster-balanced splits: train/dev/holdout to prevent overfitting to one corruption type.

### Benchmarking requirements

- Compute recovery metrics (defined later) per run and trend them over time.
- Offer “benchmark gates” for regressions (e.g., never drop overall success rate or per-cluster rate beyond thresholds).
- Store attempt counts and time per strategy to understand cost vs gain.

### Reporting requirements

- For each file: classification, attempts summary, best outputs, and “next ideas” or cluster assignment.
- For each run: overall rates, per-format rates, per-cluster rates, strategy leaderboard, and error taxonomy.

### CLI/engine requirements

- Engine must be invokable as a CLI with stable inputs/outputs.
- Provide subcommands that map to pipeline stages (scan, classify, recover, report, benchmark).

### Desktop-app requirements

- Desktop UI must act as a shell around the same core engine, not a separate logic stack.
- UI must support: project/workspace browsing, batch job submission, progress monitoring, preview of recovered artifacts, and failure cluster inspection.

### Offline-first requirements

- All state stored locally (workspace directory).
- Optional “update checks” must be disabled by default and not required for correct operation.

### Image + video support requirements

- Image families: JPEG/JPG, PNG, GIF, BMP, TIFF, WebP, HEIC/HEIF, AVIF, JPEG 2000, plus an architecture for RAW support.
- Video families: MP4/MOV, AVI, MKV/WEBM, MPEG-TS/PS, FLV, WMV/ASF.
- For each family, the architecture must support: parser/validator, repair strategies, decoder adapters, and output modes.

### Optional local API requirements (only if justified)

A local API is justified only if it simplifies desktop integration and enables a stable boundary. If used, it must be local-only (localhost/IPC) and optional. The default should be direct in-process engine usage for a desktop app to minimise failure modes.

## Stack, data model, and experimentation infrastructure

**7. Technical Stack Recommendation and Selection Matrix**

### Primary implementation language(s): recommendation

**Recommendation:** a **Rust primary core** (engine + job runner + storage + parsers) with an optional **Python “strategy lab” layer** for rapid prototyping of new strategies and scorers.

**Why this is the best fit for Uncorrupter’s targets.**

- Recovery success will come from running many heavy strategies safely over untrusted binary inputs. Rust’s memory safety reduces crash risk during aggressive parsing and candidate construction (important when you eventually parse container formats deeply).
- Offline-first desktop integration becomes much cleaner if your engine is a native library and the UI shell is a thin layer calling it.
- Python is still extremely valuable for rapid experimentation (new heuristics, new scoring signals, quick parsers), but it should be an optional layer, not the only execution model.

### Decoder and repair tool integration: recommendation

Use a **tiered adapter system**:

1) **In-process libraries** for still-image decoding and validation where mature libraries exist (JPEG/PNG/TIFF/WebP/HEIF/AVIF/JPEG2000/RAW via system libraries). This enables richer error telemetry than shelling out.
2) **External tool adapters** for video and container repair where tooling is best-in-class and stable:
   - FFmpeg/ffprobe as the universal decode/remux backend; parameterised per strategy. citeturn1search1turn8search15turn1search0
   - untrunc for reference-assisted MP4/MOV moov rebuild. citeturn0search0turn0search6
   - Bento4 toolchain for MP4 box inspection/editing as needed. citeturn5search1turn5search5
   - TSDuck for TS resync (high-success class). citeturn5search3

### Configuration system

- Use TOML for human-edited configs (stable, readable, diff-friendly).
- Each run stores an immutable config snapshot.

### Plugin system

- Core plugin ABI: Rust trait-based plugins compiled into the binary for baseline releases.
- Experimental plugin lane: Python strategies loaded via a “strategy host” that communicates with the core through a narrow, versioned interface (e.g., JSON schema over stdin/stdout or an embedded interpreter).
- Every plugin declares: version, strategy ID namespace, applicable families, and parameter schema.

### Database and storage model: recommendation

**Primary DB:** SQLite for transactional metadata (runs, files, attempts, outputs, job state).  
SQLite is appropriate for offline-first embedded apps, but concurrency parameters and transaction sizing matter; WAL mode improves read/write concurrency but is not ideal for huge transactions. citeturn10search2turn10search11

**Artifact store:** content-addressed blob store on disk (SHA-256 addressed), with compaction and deduplication.

**Analytics export:** Parquet for large attempt logs and run analytics (optional but strongly recommended once you scale). citeturn10search12

### Queue/task execution model

- Local job runner with:
  - per-file budgets (time, attempts, CPU),
  - per-strategy budgets (top-K, stop conditions),
  - global concurrency control,
  - strict timeouts for external tools.

### Testing and benchmarking framework

- Rust core: cargo test + property-based tests (e.g., proptest) for parsers and candidate constructors.
- Fuzzing lane for parsers (important for untrusted binary parsing).
- Benchmark harness integrated as a first-class command, producing run IDs and comparable reports (aligned with NIST “repeatable testing” expectations for forensic tools). citeturn9search9turn9search1

### Packaging/distribution approach (offline-first desktop)

**Desktop framework recommendation:** Tauri v2 for cross-platform desktop shells around native Rust backends. citeturn10search3turn10search13  
Why: it supports shipping a native backend with a UI written in any web framework, remaining offline-first by design.

**What to avoid even if popular.**

- Electron as default: not because it can’t work, but because Uncorrupter’s core complexity is not UI; you want to keep the shell thin and reduce packaging bloat and moving parts.
- A “web service first” architecture: it undermines offline-first goals and complicates file access, performance, and user trust.

**Selection matrix (high-level)**

| Choice point | Options considered | Best option for Uncorrupter | Why it wins here |
|---|---|---|---|
| Core language | Rust / Python / C++ / Go | Rust (+ optional Python lab) | Safety + performance + native desktop integration; Python retained for experimentation |
| Video decode/remux | FFmpeg CLI / libav* direct / bespoke | FFmpeg CLI strategies | Widest support; configurable error tolerance (`ignore_err`, `discardcorrupt`) citeturn1search1turn8search15 |
| MP4 box tooling | Bento4 / GPAC / custom | Bento4 + untrunc optional | Precise box tooling + proven truncated repair workflow citeturn5search1turn0search0 |
| Primary metadata DB | SQLite / DuckDB / Postgres | SQLite | Embedded, offline, transactional; WAL carefully used citeturn10search2turn10search11 |
| Attempt analytics | SQLite only / Parquet / DuckDB | SQLite + Parquet exports | SQLite for state; Parquet for large analytical scans citeturn10search12 |
| Desktop shell | Tauri / Qt / Electron | Tauri | Native backend boundary, cross-platform tooling citeturn10search3turn10search13 |

**8. Knowledge Model and Data Model (media-generic)**

### Core principle: “evidence first, artifacts second”

Every decision the system makes must be reconstructible from stored evidence:

- “Why was this classified as JPEG missing SOI?”
- “Which byte offsets were used to build the winning candidate?”
- “Which decoder flags produced these frames?”
- “What changed between run 41 and run 42?”

### Target schema (logical; implementable in SQLite + blob store)

**Workspace**
- workspace_id, created_at, schema_version, engine_version, config_snapshot_hash
- roots: input_root, output_root, corpora_root

**Files**
- file_id, workspace_id
- original_path, relative_path
- size_bytes, sha256
- declared_type (extension), detected_type_byte0, detected_type_anywhere
- signature_index (summary), marker_stats (json)
- corruption_hypotheses (json)
- classification_family, classification_label, classification_confidence, classification_evidence_json

**Signatures (index of “found anywhere”)**
- signature_id, file_id
- family (jpeg/png/isobmff/ebml/mpegts/…)
- offset, signature_type, confidence

**Candidates (first-class, not just slices)**
- candidate_id, file_id, strategy_id, strategy_version
- candidate_kind: `slice` | `synthetic_header` | `fragment_graph` | `container_rebuild_plan`
- payload_ref: points into blob store or references segment lists
- provenance: parent candidate(s), transformations applied
- estimated_cost: bytes_read, expected_decode_time
- dedupe_hash: hash over canonical candidate representation

**Decoder attempts**
- attempt_id, file_id, candidate_id
- decoder_id (pillow/libjpeg/ffmpeg/…)
- decoder_config_id (flags/options)
- phase: probe | full_decode | extract_frames | remux
- start_time, duration_ms, timeout_hit, exit_code
- success boolean
- structured_result: width/height, pixel_format, duration, frames_decoded, streams_found, warnings_count
- stderr_excerpt, error_code, error_taxonomy_label
- validation_signals: structural_ok, crc_ok, box_tree_ok, etc.
- score_total + score_components (json)

**Outputs (multi-artifact)**
- output_id, attempt_id, output_type: image | video | frame_set | elementary_streams | diagnostic_dump
- artifact_hash, artifact_path
- summary metadata (dimensions/duration/frame_count), preview_path
- “usefulness score” and confidence

**Frames (video-derived)**
- frame_id, output_id
- timestamp_pts, is_keyframe, decode_warnings
- image_artifact_hash/path
- per-frame quality heuristics

**Runs and benchmarks**
- run_id, workspace_id, run_type: scan | recover | benchmark
- strategy_set_id, decoder_set_id, config_snapshot_hash
- aggregate metrics table (overall + per-family + per-cluster)
- regression links to previous runs

**Failure clusters**
- cluster_id, definition_version
- rules (feature predicates), exemplar files, strategy recommendations
- per-run cluster performance tracking

This schema supports images and videos without forcing a “single output file” model and makes frame extraction first-class.

## Recovery engine and desktop architecture

**9. Recovery Architecture (next-generation target)**

The architecture must be **media-generic at the top** and **family-specific below**.

### Top-level pipeline (media-generic)

1) **Intake + manifesting**
   - Enumerate inputs, compute hashes, register in DB.
   - Build an “evidence record”: signatures at byte 0 and “anywhere signatures”.

2) **Triage/classification**
   - Produce family + label + confidence + evidence JSON.
   - Populate feature vectors for clustering (marker counts, offset distributions, container scan summaries).

3) **Strategy engine**
   - Select strategy families based on classification and budgets.
   - Generate candidates (potential reconstructions) with provenance.

4) **Candidate dedupe + scheduling**
   - Canonicalise candidates, dedupe by representation hash.
   - Prioritise by expected success (classification priors) and cost.

5) **Decoder adapter layer**
   - Execute decoder attempts (probe first, then full decode/extraction).
   - Capture structured telemetry and bounded logs.

6) **Validation/scoring**
   - Combine structural validation, decoder diagnostics, output magnitude, and content heuristics.
   - Promote top candidates; optionally continue exploration if marginal improvements exist.

7) **Output normalisation**
   - For images: export viewable PNG/JPEG plus a “raw candidate” artifact if requested.
   - For videos: produce one or more of {remuxed playable output, clips, extracted frames, elementary streams}.

8) **Evidence store + reporting**
   - Persist everything; produce per-file and per-run reports.
   - Update cluster statistics and strategy leaderboards.

### Family engines (below pipeline)

Each family engine encapsulates:

- Parser/validator (structural understanding).
- Candidate generators (repair strategies).
- Decoder configs (tolerant vs strict).
- Output builders (normalisers and exporters).
- Scoring hooks (family-specific signals).

**10. Local/Offline-First Desktop Application Architecture**

### Embed vs wrap

**Recommendation:** embed the core engine as a library in the desktop backend (same process), but execute recover jobs in background tasks with strict resource controls. This avoids IPC brittleness in an offline tool that must handle huge files and heavy outputs.

### Desktop framework recommendation

Tauri v2 is a good fit for an offline-first shell over a Rust engine. citeturn10search3turn10search13  
If you later decide to keep a Python-heavy engine, Qt for Python + PyInstaller is viable, but packaging complexity tends to grow with native dependencies. citeturn10search1

### Workspace model

A workspace is a directory containing:

- `workspace.sqlite` (metadata DB)
- `blobs/` (content-addressed artifacts)
- `outputs/` (user-facing exports, grouped by run and file)
- `reports/` (JSON/CSV/HTML summaries)
- `corpora/` (optional referenced corpora indexes)
- `configs/` (snapshots of run configs)

### Local queue/job model

- Jobs are persisted in the DB: pending/running/complete/failed.
- Workers read jobs and write progress checkpoints.
- UI reads progress from DB and tail logs.

### Batch-run UX (engine-first)

The UI must support:

- Select input roots; preview detected families and clusters.
- Choose strategy presets: baseline, aggressive, “deep JPEG”, “deep MP4”, etc.
- Show progress: files processed, candidates tried, decoder timeouts, recovered artifacts.
- For each file: show classification, best outputs, attempt timeline, and error taxonomy.

### Failure-inspection UX

- Cluster view: see top failing clusters, exemplar files, and recommended strategies/tests to add next.
- Diff view: compare two runs and show what improved/regressed by cluster.

### Safe handling of large files and many outputs

- Never duplicate input blobs unless asked; work with memory-mapped reads.
- Store outputs content-addressed; link them into user-visible folders.
- Enforce output quotas per run unless user opts out.

### Update model

- Offline-first default: no auto-update required for functionality.
- If updates exist, they should be explicit user actions and never required for a recovery job.

### Out of scope for v1 desktop release

- Cloud sync, multi-machine orchestration, online account features.
- Collaborative UI features.
- “One-click perfection” promises; instead ship a transparent recovery lab with presets.

**17. Recommended Repository / System Structure (concrete target)**

A Rust-first repo structure that cleanly separates core, family engines, adapters, and desktop:

```text
uncorrupter/
  crates/
    uncorrupter-core/
      src/
        workspace/          # DB, blob store, schema migrations
        intake/             # scanning, hashing, signature indexing
        triage/             # family detection + classification
        strategy/           # candidate model, dedupe, scheduling
        decoders/           # decoder adapters + telemetry schema
        scoring/            # scoring framework + shared signals
        reporting/          # report generation + exports
        formats/
          jpeg/
          png/
          gif/
          bmp/
          tiff/
          webp/
          isobmff/          # mp4/mov/heif/avif shared box parsing
          matroska/
          riff/             # avi/wav-like parsing
          mpegts/
          flv/
          asf/
    uncorrupter-cli/
      src/                  # CLI commands: scan/classify/recover/benchmark/report
    uncorrupter-desktop/
      src-tauri/            # Tauri backend; calls uncorrupter-core
      ui/                   # frontend code
  strategy-lab/             # optional Python-based rapid strategy prototyping
  corpora/
    fixtures/               # synthetic + real regression fixtures
    mutation-recipes/       # corruption generator configs
  docs/
    format-notes/           # format deep dives + strategy catalogues
    benchmarks/             # benchmark definitions + dashboards
  tools/
    external-adapters/      # wrappers for ffmpeg, bento4, untrunc, tsduck, etc.
```

This structure is designed so that engines can be expanded without contaminating the core pipeline.

## Format-specific design, triage, scoring, testing, benchmarks, development blueprint, immediate recommendations, and final blueprint

**11. Format-Specific Recovery Research and Design (mechanism-first)**

This section is intentionally “strategy-centric”: each family gets (a) corruption patterns, (b) what works, (c) what fails, (d) what to validate, and (e) hard limits.

### JPEG (deep focus)

**Common corruption patterns (relevant to your evidence).**
- Missing SOI and early header segments (dominant per run evidence: internal structure but no SOI). fileciteturn5file0
- Missing EOI (common per run evidence). fileciteturn5file0
- Missing DHT but SOS present (noted explicitly). fileciteturn5file0
- Truncation within entropy-coded scan data.
- Fragmentation (scan data split/displaced).

**Prior art and what to adopt.**
- Use the JPEG spec’s segment definitions to build a **segment parser** able to scan for DQT/DHT/SOF/SOS segments and validate lengths. citeturn2search1turn2search5
- Adopt forensic “object validation”: any candidate assembly must be validated via strict parsing + decoder behaviour, not just “marker presence”. citeturn9search2turn9search6
- Add a **missing-DHT injection** family; run evidence says it matters. fileciteturn5file0

**Concrete strategy families Uncorrupter must implement.**
1) **SOI/EOI reconstruction**
   - If SOI missing: build synthetic SOI, but *only* after constructing a plausible header sequence (SOF, DQT, DHT, DRI as applicable).
   - If EOI missing: append EOI only after ensuring scan data ends at a plausible boundary; otherwise allow truncated decode.

2) **Header rebuild from scattered segments**
   - Scan entire blob for valid segment candidates (APP0/APP1/DQT/DHT/SOF).
   - Construct multiple header hypotheses:
     - “Use found DQT + inject standard DHT”
     - “Use found DHT + default DQT”
     - “Use earliest plausible SOF near SOS”
   - Pair header hypotheses with scan-data windows (SOS→end, SOS→EOI candidates, restart-marker bounded windows).
   - This is the category most aligned with your observed winning strategy `jpeg_rebuilt_header_from_segments`. fileciteturn5file0

3) **Restart-marker resynchronisation**
   - If restart markers exist, use them to define independently decodable runs; restart markers reset predictor states and resynchronise decoding, which can enable partial recovery even with corruption. (This is widely cited in JPEG literature; practical effect: decode blocks between restarts.)

4) **Entropy-stream salvage**
   - When scan data is corrupted, attempt:
     - windowed decode starting at different offsets,
     - “truncate at first hard error” decode to salvage the prefix region,
     - fragment continuation search (aggressive mode).

5) **Fragment graph reassembly (aggressive mode)**
   - Use fragmentation-point detection techniques to propose continuations and validate via decoder success. citeturn2search12turn2search8

**Scoring/validation signals (must be JPEG-aware).**
- Header coherence: presence and ordering of SOI → (APP*) → DQT → DHT → SOF → SOS.
- Decoder warning profile: “missing Huffman table” vs “invalid SOS parameters” vs “premature end”.
- Output plausibility: dimensions not extreme; entropy not degenerate; consistent MCU grid artefacts can still be valid partial recovery.

**Hard limits.**
- If SOF is missing and dimensions cannot be inferred, baseline decoders cannot reconstruct pixels; recovery may require brute-force dimension inference, which is expensive and uncertain.
- If entropy-coded scan is heavily overwritten, recovery may be limited to small prefixes.

### PNG

**Structure constraints.** PNG is a signature + chunk sequence; a valid PNG must include IHDR, IDAT, IEND. citeturn3search0turn3search16

**What works.**
- If signature missing but IHDR present: prepend signature and attempt chunk parsing.
- If IEND missing: append IEND and attempt decode.
- If chunk length/CRC corrupt: try repairing chunk boundaries and CRCs (validator-guided).

**What fails.**
- Corrupted IDAT/zlib stream often kills decode; validation tools emphasise detection rather than robust partial repair. citeturn3search13turn3search1

**Validation/scoring.**
- Chunk ordering and CRC status (like pngcheck does). citeturn3search13
- Partial decode may need a “row salvage” approach only if you implement custom zlib recovery logic (advanced).

### GIF

**What works.**
- Header/trailer (`0x3B`) reconstruction and block parsing.
- First-frame salvage is often feasible; full animation salvage requires deeper parsing and LZW stream recovery.

**What fails.**
- LZW stream corruption can desynchronise decoding; often yields early-frame salvage only.

### BMP

BMP is relatively forgiving if headers remain: fix file size, pixel offset, DIB header fields. Reference material describes fixed header structures and pixel storage rules. citeturn4search6turn4search10

### TIFF

TIFF repair is mostly “offset table integrity”:

- Repair IFD chains and strip/tile offsets; TIFF spec guidance around strip offsets and compatibility is relevant. citeturn4search0turn4search8

### WebP

WebP is RIFF-based; container sizing and chunk structure matter. citeturn3search6turn3search2turn3search18  
Strategies: repair RIFF size fields, locate VP8/VP8L/VP8X chunks, attempt subtype-specific decode.

### HEIC/HEIF and AVIF

Treat as ISOBMFF containers:

- libheif supports HEIF/AVIF decoding. citeturn7search0
- AVIF is explicitly AV1-in-HEIF/ISOBMFF per spec. citeturn7search1turn7search9  
Strategies: box scanning, missing box reconstruction, and fallback to frame/image item extraction even when full container parse fails.

### JPEG 2000

Use OpenJPEG-based decoding paths; codestream/JP2 parsing should be validator-driven. citeturn7search10turn7search2

### RAW-family support

Use LibRaw for decoding attempts and metadata salvage. citeturn7search3turn7search7  
Architecturally, RAW support belongs as a plugin family with separate licensing/packaging considerations.

### Video families (deep focus)

**MP4/MOV**
- Box tree structure is foundational; tools like Bento4 exist specifically to inspect and manipulate it. citeturn5search5turn5search1
- Missing `moov` is common in abrupt shutdown scenarios; untrunc addresses this with reference files. citeturn0search0turn0search6  
Strategies:
- “Box scan + salvage `mdat` ranges”
- “Reference-assisted moov rebuild”
- “FFmpeg tolerant demux → remux → transcode” presets

**AVI**
- Header/index rebuild (idx1) strategies inspired by DivFix++’s described behaviour. citeturn6search4turn6search16

**MKV/WEBM**
- Matroska EBML structure and ordering guidance; cues rebuild strategies. citeturn6search5turn6search1

**MPEG-TS/PS**
- Strong candidate for very high recovery rates: fixed packet size, sync byte, resync utilities exist. citeturn5search11turn5search3

**FLV**
- Tag-based parsing with constraints; salvage by scanning tags and reconstructing metadata. citeturn6search2turn6search14

**WMV/ASF**
- Object-based structure: required header+data, optional index. citeturn6search3turn6search7  
Strategies: object scan, rebuild minimal header, extract stream packets.

**12. Classification and Triage System (actionable clusters)**

Classification must drive strategy selection and must remain explainable.

### Core labels (minimum viable set)

**Image clusters (examples)**
- `jpeg_missing_soi_internal_structure` (matches your dominant failure class) fileciteturn5file0
- `jpeg_missing_eoi`
- `jpeg_missing_dht`
- `jpeg_truncated_scan`
- `png_missing_signature_but_ihdr_present`
- `png_missing_iend`
- `png_idat_corrupt_crc_or_zlib`
- `tiff_ifd_or_strip_offsets_corrupt`
- `webp_riff_size_or_chunk_order_corrupt`

**Video/container clusters (examples)**
- `isobmff_missing_moov`
- `isobmff_truncated_mdat`
- `riff_avi_missing_idx1`
- `ebml_missing_cues_or_truncated_segment`
- `mpegts_desync_or_partial_packets`
- `asf_missing_index_or_truncated_objects`
- `flv_truncated_tags`

### Decision logic (layered)

1) **Family detection**
   - Byte-0 signature if present.
   - Anywhere-signature hits (signature index).
   - Container heuristics (ISOBMFF box headers, EBML header IDs, TS sync patterns).

2) **Cluster assignment**
   - For each family, compute structural marker features.
   - Apply ordered rules → assign label + confidence.
   - Store evidence JSON and feature vector.

3) **How classification influences strategy selection**
   - Choose “cheap high-yield” strategies first (e.g., append EOI, missing signature repair).
   - Escalate to reconstruction strategies for high-confidence deep corruption.
   - Trigger aggressive modes (fragment graphs) only for clusters where it is justified.

**13. Candidate Generation and Scoring Framework (aggressive without explosion)**

### Candidate creation principles

- Every candidate must have provenance and a canonical representation (to dedupe).
- Candidate generation must be structured as “families of hypotheses”, not a flat list.

### Explosion control mechanisms

- **Budgeting:** per file and per strategy budgets (attempt count, time, CPU).
- **Progressive deepening:** run cheap strategies first; only expand when they fail.
- **Dedupe:** hash canonical candidate descriptions (segment lists, offset windows, reconstructed headers).
- **Adaptive scheduling:** use cluster priors (learned from past runs) to prioritise strategies that historically work for that cluster.

### Scoring without ground truth (multi-signal)

At minimum score components should include:

- Decode success (hard gate).
- Magnitude: image area; video duration/frame count.
- Structural plausibility: valid chunk/segment sequences (PNG IHDR/IDAT/IEND; MP4 box tree; Matroska EBML sanity).
- Decoder telemetry: warnings count, error types, “ignore_err” usage; FFmpeg flags explicitly note that ignoring errors is useful for analysis but not guaranteed to yield pleasing output. citeturn1search1turn1search0
- Content heuristics: entropy/variance, edge density, non-trivial histogram.

**14. Testing and Improvement System (failure → fixture → regression lock-in)**

This system must be designed to operationalise the NIST-style demand for repeatable, testable forensic tooling. citeturn9search9turn9search1

### Test layers

- **Unit tests:** marker parsers, chunk parsers, box parsers, EBML readers.
- **Strategy tests:** given a synthetic corruption fixture, strategy X must produce candidate Y with expected validation signals.
- **Decoder adapter tests:** ensure FFmpeg/Pillow/lib* adapters produce stable telemetry and timeouts.
- **Corruption fixtures:** real-world failed files curated into a regression suite, organised by cluster.
- **Synthetic mutation tests:** start from known-good corpus, apply controlled corruptions (truncate header, remove moov, flip chunk length, split TS packets), and validate expected recovery outcomes.
- **Property/fuzz tests:** for parsers (especially ISOBMFF/EBML/RIFF), because untrusted binary parsing is a high-risk surface.

### Workflow: new failure becomes progress

1) Failure appears in a benchmark run.
2) System auto-assigns cluster; if “unknown”, it triggers cluster creation workflow.
3) Failure file becomes a fixture (with metadata, constraints, and optional ground truth).
4) A new strategy or repair is implemented.
5) Benchmarks rerun; regression gates must pass.

**15. Benchmarking and Evaluation**

Uncorrupter must track multiple metrics because “recovery success” is multi-dimensional.

### Image metrics

- Strict decode rate.
- Partial-viewable rate (above threshold area and non-degenerate content).
- Per-format and per-cluster rates.
- False-positive rate (decode success but fails plausibility checks).
- Average candidates tried; average time.

### Video metrics

- Playable output rate.
- Seekable output rate (when measurable).
- Frame salvage rate (keyframes recovered; total frames recovered).
- Per-container-family rates.
- Audio salvage rate (when applicable).
- Clip salvage coverage (total recovered duration / estimated duration).

### No-ground-truth ranking metrics

- Cross-decoder agreement.
- Structural validation scores.
- Stability: the same input under the same run config yields the same ranked output.

### Holdout strategy

- Maintain a holdout set per corruption cluster to detect overfitting (especially for JPEG header rebuild heuristics and MP4 repair heuristics).

**16. Development Process (sequenced, practical roadmap)**

A sequenced plan optimised for maximum recovery rate:

1) **Architecture consolidation phase**
   - Freeze the schema, pipeline interfaces, strategy plugin model.
   - Implement media-generic intake and signature indexing (byte-0 + anywhere signatures).
   - Add benchmarking harness + run DB integration as mandatory.

2) **Baseline multi-format image phase**
   - Implement family engines for JPEG/PNG/GIF/BMP/TIFF/WebP with validators.
   - Bring over v1 marker diagnostics breadth into v2 architecture.

3) **Deep JPEG phase (highest ROI given evidence)**
   - Implement missing DHT injection strategies (explicitly required by your run evidence). fileciteturn5file0
   - Implement robust header rebuild from scattered segments (institutionalise `jpeg_rebuilt_header_from_segments` concept). fileciteturn5file0
   - Add restart-marker bounded decode strategies.
   - Add fragment-graph mode as an optional aggressive strategy lane.

4) **Video baseline phase**
   - Integrate FFmpeg adapter presets (tolerant demux/decode, remux, frame extraction). citeturn1search1turn8search15
   - Implement container-family detection (ISOBMFF, RIFF/AVI, EBML, TS, ASF, FLV).
   - For each family, start with “extract what you can” outputs (frames/clips) before ambitious full repair.

5) **Container repair deepening**
   - MP4/MOV: integrate Bento4 diagnostics + optional untrunc reference-assisted repair. citeturn5search5turn0search0
   - AVI: implement idx1 rebuild strategy inspired by DivFix++ logic. citeturn6search4
   - TS: integrate resync logic (tsresync-like). citeturn5search3
   - MKV: implement cues rebuild and remux strategies guided by Matroska spec/order. citeturn6search5turn6search1

6) **Scoring and clustering maturation**
   - Train cluster priors from benchmark history.
   - Improve false-positive suppression.

7) **Desktop shell integration**
   - Build minimal UI around job queue, preview, and failure cluster dashboards.
   - Keep core engine unchanged; UI is a thin shell.

8) **Optimisation only after capability**
   - Speed optimisations come last; the primary target is success rate.

**18. Immediate Recommendations for the Current Project (based on the uploaded evidence)**

This section is prioritised for “max recovery rate increase per unit work”.

### Highest-value next research conclusions

- Your failure distribution is dominated by “JPEG but missing start-of-file integrity”; byte-0 signatures are almost always gone. fileciteturn5file0 Any future approach must treat “header reconstruction” as the central task, not an edge case.
- Missing DHT appears often enough that it must become a baseline JPEG strategy family. fileciteturn5file0

### Highest-value next architecture decisions

- Use `Uncorrupter.zip`’s modular pipeline and database as the base architecture (it is the correct long-term spine).
- Replace the current candidate model with a richer representation that supports: synthetic header construction, fragment graphs, and container rebuild plans.

### Most important missing strategy families (immediate)

1) **JPEG missing-DHT injection baseline** (because your own run evidence says SOS-but-no-DHT occurs). fileciteturn5file0  
2) **JPEG header rebuild (robust, not ad hoc)**: generalise the idea behind the winning `jpeg_rebuilt_header_from_segments` strategy into a maintained, tested module. fileciteturn5file0  
3) **Video-first salvage path**: FFmpeg-based tolerant decode + frame extraction presets must exist early, because it immediately turns many “unplayable” cases into valuable recovered frames. citeturn1search1turn8search15  
4) **ISOBMFF missing moov playbook**: integrate untrunc as optional aggressive mode and ensure corpus tooling can store reference files. citeturn0search0turn0search6

### Most important missing tests

- Regression fixtures for the top JPEG clusters: missing SOI, missing EOI, missing DHT.
- Synthetic corruption generator tests for those clusters.
- Video container fixtures: MP4 missing moov, AVI missing idx1, TS desync.

### Is the current v2 architecture the right base?

Yes for the pipeline/evidence/CLI spine. No for its current “JPEG-only worldview”; it must be made media-generic immediately.

### What from v1 should be ported, evolved, or replaced

- Port: broad signature/marker statistics and candidate-family thinking (but re-implement within the plugin architecture).
- Replace: extension-trusted-only as a default; keep it as a user-selectable policy.

### What must change because the target is now any image and video type

- Candidate and output models must become **multi-artifact** and **multi-fragment**.
- Storage must handle massive outputs; content-addressing is no longer optional.

**19. Final Source-of-Truth Blueprint (for a later implementation run)**

### Confirmed conclusions from uploaded evidence

- Recovery rate is currently ~0.47% on the provided run (`11/2328`). fileciteturn5file0
- Nearly everything is declared JPEG, and byte-0 signatures are almost always absent. fileciteturn5file0
- The dominant failure cause is “no_candidate_succeeded”. fileciteturn5file0
- The few wins largely came from “rebuilt header from segments”, indicating header reconstruction is the essential capability class. fileciteturn5file0
- `a.py` is intentionally candidate-generation-focused and extension-first, with Pillow and optional FFmpeg decode. fileciteturn3file0

### Confirmed conclusions inferred from external research

- Signature-based carving tools are effective but limited by fragmentation; object validation is a key mechanism to improve carving quality. citeturn0search1turn9search2turn9search6
- MP4/MOV truncation repair often revolves around reconstructing `moov`; tools like untrunc require a similar reference file. citeturn0search0turn0search6turn5search0
- MPEG-TS is structurally resilient and resynchronisation tooling exists (`tsresync`), making it a high-yield target for video recovery. citeturn5search3turn5search11
- FFmpeg exposes explicit error-tolerance knobs (`ignore_err`, `discardcorrupt`) that should be treated as strategy parameters, not a single fixed command. citeturn1search1turn8search15turn1search0
- PNG’s chunk model and CRC tooling support structural repair attempts, but zlib corruption limits partial recovery in many cases. citeturn3search0turn3search13turn3search16
- AVIF and HEIF are ISOBMFF-derived; treating them as container + codec payload aligns image and video repair approaches. citeturn7search1turn7search9turn7search0
- ASF/WMV is object-structured with required header/data and optional index; repair is object/table reconstruction. citeturn6search3turn6search7
- Matroska has standards-track specification (RFC 9559) and ordering guidance relevant to seekability. citeturn6search5turn6search1

### Hypotheses that still need validation (explicitly uncertain)

- Whether your dataset’s JPEG failures include true fragmentation (non-contiguous storage) versus “prefix loss + internal truncation” only. The “internal structure but no SOI” count supports prefix loss, but fragmentation requires deeper analysis of marker distributions and continuation validity (not fully provable from the summary alone). fileciteturn5file0
- Whether FFmpeg materially improves still-image salvage on your corpus; your run shows only Pillow successes. fileciteturn5file0 (This may reflect configuration rather than FFmpeg capability.)

### Recommended architecture decisions (locked)

- Media-generic pipeline with family engines; multi-artifact outputs; content-addressed artifact store; SQLite metadata DB.
- Candidate model upgraded to support synthetic constructions and fragment graphs.
- Classification-driven strategy selection + continuous benchmarking.

### Selected technical stack decisions (locked)

- Rust core + optional Python strategy lab.
- FFmpeg as core video adapter; optional Bento4/untrunc/TSDuck integrations as strategy backends.
- SQLite (careful WAL usage) + optional Parquet exports for analytics. citeturn10search2turn10search12
- Tauri v2 desktop shell around embedded core engine. citeturn10search3turn10search13

### Selected desktop/offline-first product decisions (locked)

- Workspace-first local storage model; no network dependency.
- UI as a thin shell around the same engine used by CLI.
- Batch-first UX: progress + cluster inspection + comparisons.

### Prioritised next implementation order (for the next GPT run)

1) Port the v2 modular pipeline into a new repo layout and make it media-generic at the top.
2) Implement signature indexing “anywhere in blob” and media-family detection beyond byte-0.
3) Implement deep JPEG repair core:
   - missing DHT injection baseline,
   - header rebuild from scattered segments,
   - restart-marker bounded decode.
4) Integrate FFmpeg strategy presets for video; add frame extraction outputs.
5) Add MP4/MOV repair lane (Bento4 diagnostics + untrunc optional).
6) Add TS resync lane (TSDuck-like).
7) Add corpus + fixture + mutation generator system; lock regressions with benchmarks.
8) Build the first desktop shell (job queue + previews + cluster dashboards).