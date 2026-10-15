# Feature Specification: Stabilized Multi-Format Recovery

**Feature Branch**: 001-stabilize-multiformat-recovery

**Created**: 2026-07-26

**Status**: Approved for implementation

**Input**: User description: "Implement all fixes and format possibilities documented in docs/CAPABILITIES-AND-ROADMAP.md."

## User Scenarios & Testing

### User Story 1 - Recover Untrusted Files Safely (Priority: P1)

As a user preserving damaged files, I can run recovery without modifying originals, overwriting prior outputs, escaping the selected output location, or allowing one hostile file to consume unbounded resources.

**Why this priority**: Data preservation and bounded execution are prerequisites for every format and every later capability.

**Independent Test**: Process valid, corrupt, oversized, changing, inaccessible, symlinked, and path-traversal fixtures with strict limits and demonstrate immutable inputs, deterministic safe outputs, bounded execution, and explicit results.

**Acceptance Scenarios**:

1. **Given** an input tree and an empty output directory, **When** recovery completes, **Then** every source file is byte-for-byte unchanged and every artifact is written under the selected output root.
2. **Given** an existing output with the same intended name, **When** recovery runs without explicit replacement authorization, **Then** the existing file is preserved and the new outcome reports a collision.
3. **Given** a file or decoder that exceeds a configured limit, **When** the limit is reached, **Then** only that bounded operation stops, temporary material is cleaned up, and the run records the exact budget outcome.
4. **Given** output, workspace, or database paths inside the input tree, **When** the user has not explicitly accepted that layout, **Then** the run is rejected before processing.

---

### User Story 2 - Run, Resume, Inspect, And Cancel Recovery (Priority: P1)

As a user processing a large collection, I can observe file-level progress, cancel safely, resume an interrupted run without silently processing changed inputs, and obtain durable evidence for every result.

**Why this priority**: Long-running recovery cannot be dependable without lifecycle state, bounded commits, and resumability.

**Independent Test**: Start a mixed-format run, interrupt it after several files, inspect its persisted state and progress stream, resume it, and verify that completed unchanged inputs are reused while changed inputs are re-evaluated or rejected according to policy.

**Acceptance Scenarios**:

1. **Given** a new run, **When** processing starts and ends normally, **Then** its lifecycle moves through created, running, and completed or partial states with timestamps.
2. **Given** a cancellation request, **When** a file operation reaches a safe checkpoint, **Then** subprocesses and temporary artifacts stop cleanly and the run becomes cancelled.
3. **Given** a resumable run, **When** source identity still matches, **Then** completed files are not repeated and pending files continue deterministically.
4. **Given** a source that changed since the original run, **When** resume begins, **Then** the change is reported and the configured reprocess-or-reject policy is applied.

---

### User Story 3 - Know Exactly What Is Supported (Priority: P1)

As a user or integrator, I can query a machine-readable and human-readable capability manifest that distinguishes detection, inspection, validation, repair, normalization, extraction, preview, dependencies, limits, and test evidence.

**Why this priority**: Truthful support reporting prevents detect-only formats from being mistaken for reliable recovery.

**Independent Test**: Query capabilities in both output modes and compare them with registered handlers and fixture evidence; no advertised operation may lack an executable handler and validation scenario.

**Acceptance Scenarios**:

1. **Given** the installed application, **When** capabilities are requested, **Then** every public format lists its operation levels, required tools, encryption behavior, default budgets, and tested scenarios.
2. **Given** an optional tool is unavailable, **When** capabilities are requested or recovery is attempted, **Then** the affected operation is reported as unavailable without hiding other operations.
3. **Given** a recovery goal such as repair, normalize, extract, preview, or carve, **When** a handler cannot meet that goal, **Then** the request fails explicitly rather than substituting a weaker outcome.

---

### User Story 4 - Recover Text And Structured Text Without Inventing Content (Priority: P2)

As a user with damaged TXT, Markdown, logs, CSV, JSON, XML, or HTML, I can recover decodable byte ranges, preserve provenance, receive structural diagnostics, and optionally create normalized derivatives without fabricated prose.

**Why this priority**: Text provides a low-risk vertical slice for the new handler, artifact, and budget contracts.

**Independent Test**: Recover fixtures covering Unicode byte-order marks, invalid byte spans, mixed newlines, embedded NULs, truncated structured data, and binary contamination; compare every recovered span with its original byte offsets.

**Acceptance Scenarios**:

1. **Given** partially invalid text, **When** recovery runs, **Then** valid ranges and damaged byte ranges are reported separately with a source-offset map.
2. **Given** JSON, XML, CSV, HTML, or Markdown, **When** decoding succeeds, **Then** structural validation or diagnostics are emitted without silently changing semantics.
3. **Given** optional newline or encoding normalization, **When** requested, **Then** it is emitted as a derived artifact while the byte-preserving recovery remains available.

---

### User Story 5 - Recover Archives And Package Documents (Priority: P2)

As a user with a damaged ZIP, TAR, DOCX, XLSX, PPTX, ODT, ODS, or ODP file, I can validate its structure, rebuild only unambiguous container metadata, extract independently valid members safely, and distinguish full-package recovery from partial content extraction.

**Why this priority**: A safe archive foundation unlocks several high-value document families.

**Independent Test**: Process valid, truncated, missing-directory, CRC-damaged, duplicate-name, encrypted, nested, traversal, compression-bomb, and partially readable fixtures and verify bounded reconstruction or extraction.

**Acceptance Scenarios**:

1. **Given** a ZIP with missing or damaged directory metadata but valid local members, **When** recovery runs, **Then** recoverable members can be validated and placed in a new archive without modifying the source.
2. **Given** a package document, **When** required parts and relationships are intact or unambiguously recoverable, **Then** a validated package is produced; otherwise separate text, media, attachment, and diagnostic artifacts are produced.
3. **Given** an archive member containing an absolute path, parent traversal, device name, link escape, excessive expansion, excessive nesting, or duplicate collision, **When** extraction is attempted, **Then** the member is contained, renamed, skipped, or rejected according to a recorded safe policy.
4. **Given** encrypted content, **When** no authorized password is supplied, **Then** encryption is reported and no cracking or execution is attempted.

---

### User Story 6 - Recover PDF Content Conservatively (Priority: P3)

As a user with a damaged PDF, I can receive structural diagnostics, a conservatively rebuilt file when possible, and independently extracted pages, text, images, attachments, or metadata when full recovery is not possible.

**Why this priority**: PDF is common and valuable but requires a dedicated object and cross-reference model.

**Independent Test**: Process PDFs with prefixed bytes, missing end markers, broken start references, damaged cross-reference tables, orphan objects, malformed page trees, and embedded content; validate every claimed output independently.

**Acceptance Scenarios**:

1. **Given** a PDF with discoverable objects but broken cross-references, **When** repair is requested, **Then** a new candidate may reconstruct references and is labeled repaired only after independent validation.
2. **Given** an unrecoverable page tree with recoverable streams or attachments, **When** extraction is requested, **Then** those artifacts are returned as partial content with object provenance.
3. **Given** an optional external PDF tool or renderer is absent or times out, **When** its operation is requested, **Then** the result is explicit and core bounded analysis still completes where possible.

---

### User Story 7 - Recover Images With Format-Aware Fidelity (Priority: P3)

As a user with damaged JPEG, PNG, GIF, BMP, TIFF, WebP, AVI/RIFF images, HEIF, AVIF, JPEG 2000, or camera RAW, I can receive format-aware diagnostics and the strongest honestly validated artifact available without losing animation or multipage content silently.

**Why this priority**: Existing image support needs truthful writing, structural validation, and fidelity grades.

**Independent Test**: Run valid and mutated fixtures for each advertised image family, including truncated headers/tails, corrupt lengths, checksums, indexes, offsets, wrong extensions, animation, multipage content, and unavailable codecs.

**Acceptance Scenarios**:

1. **Given** a structurally damaged supported image, **When** an unambiguous header, length, checksum, or trailer repair is available, **Then** a correctly suffixed, independently validated artifact is written atomically.
2. **Given** a multi-frame or multipage image, **When** only one frame can be extracted, **Then** it is labeled preview or partial content rather than full recovery.
3. **Given** a codec-dependent format, **When** the decoder or writer is unavailable, **Then** detection and extraction capabilities remain distinct from repair availability.

---

### User Story 8 - Recover Video, Audio, And Complex Containers (Priority: P3)

As a user with damaged MP4/MOV, Matroska/WebM, AVI, MPEG transport/program streams, FLV, ASF/WMV, WAV, MP3, FLAC, AAC, or Ogg, I can inspect container structure, resynchronize or carve recoverable streams, remux or extract media through bounded tools, and receive continuity/fidelity evidence.

**Why this priority**: Large media requires the shared streaming, subprocess, and artifact foundation before deeper recovery is safe.

**Independent Test**: Process container mutations and unavailable/timeout tool scenarios while measuring stream discovery, timestamps, duration, decoded coverage, warnings, cleanup, and resource use.

**Acceptance Scenarios**:

1. **Given** a prefixed, truncated, missing-index, or discontinuous media container, **When** recovery runs, **Then** structural diagnostics and any bounded remux, extracted stream, preview, or frame artifacts are graded separately.
2. **Given** a decoder timeout or failure during final output creation, **When** the process ends, **Then** the exception is contained, temporary output is removed, and the file receives an explicit failed or partial outcome.
3. **Given** audio streams inside a video or standalone audio, **When** extraction is requested, **Then** independently validated audio artifacts can be produced with continuity metadata.

---

### User Story 9 - Handle TAR, 7z, RAR, And Legacy Office Honestly (Priority: P4)

As a user with TAR, compressed TAR, 7z, RAR, DOC, XLS, PPT, or RTF, I can obtain bounded native analysis where practical or use an isolated optional-tool adapter, with full disclosure of encryption, multi-volume, solid archive, conversion, and partial-success limits.

**Why this priority**: These formats remain valuable, but proprietary or complex structures require conservative adapter-first support.

**Independent Test**: Exercise sequential TAR recovery and tool-present/tool-absent adapter paths for each external format without path escape, execution of embedded code, or misleading recovery grades.

**Acceptance Scenarios**:

1. **Given** a damaged TAR with later valid headers, **When** extraction runs, **Then** later recoverable members can be salvaged under checksum and containment rules.
2. **Given** 7z, RAR, or legacy Office input without an approved tool, **When** recovery runs, **Then** the application reports the unavailable adapter and retains detection/inspection evidence.
3. **Given** macros or embedded executable content, **When** a document is inspected or extracted, **Then** the content is preserved only as inert bytes and is never executed.

---

### User Story 10 - Reproduce And Govern Recovery Quality (Priority: P1)

As a maintainer, I can install development dependencies from project metadata, run deterministic tests on supported platforms with and without optional tools, generate mutations and benchmark reports, and prevent capability documentation from drifting from executable evidence.

**Why this priority**: Broad recovery claims require repeatable quality gates.

**Independent Test**: Start from a clean development environment, run the complete test and capability-consistency suite, run the mutation corpus twice, and compare deterministic outputs and metrics.

**Acceptance Scenarios**:

1. **Given** a clean supported environment, **When** development installation and tests run, **Then** no undeclared test dependency is required.
2. **Given** optional tools present or absent, **When** the corresponding test jobs run, **Then** both states have explicit expected results.
3. **Given** a registered capability without minimum fixtures or validation, **When** the consistency gate runs, **Then** the gate fails before release.

### Edge Cases

- Empty files, directories, and mixed trees with no supported inputs.
- Files that disappear, change size, or change identity during processing.
- Junctions, symlinks, hard links, reparse points, sparse files, reserved names, long paths, and case-insensitive collisions.
- Output, workspace, database, or temporary paths nested under one another or under input.
- Interrupted atomic replacement, full disks, permission loss, and cleanup failure.
- Candidate plans that overlap, repeat identical payloads, or exceed cumulative budgets.
- Malformed length fields, integer overflow, cyclic pointers, cyclic relationships, and recursive containers.
- Archive bombs, duplicate names, Unicode normalization collisions, links, devices, and encrypted members.
- Decoder output flooding, hangs, crashes, missing executables, version drift, and cancellation races.
- Wrong extensions, embedded valid files, polyglots, false-positive signatures, and ambiguous formats.
- Structured text with mixed encodings, malformed byte-order marks, invalid scalar values, and huge lines.
- Documents containing macros, scripts, external relationships, active content, or hostile metadata.
- Multi-frame images, multipage images, variable-frame-rate media, timestamp discontinuities, and missing indexes.
- Existing databases from earlier schema versions and partially committed runs.

## Requirements

### Functional Requirements

#### Safety And Resource Control

- **FR-001**: The system MUST treat every source file as immutable evidence and MUST never write through an input path.
- **FR-002**: The default output policy MUST preserve every existing destination and MUST require explicit authorization for replacement.
- **FR-003**: Every artifact MUST be created through a temporary sibling, validated, durably flushed, and atomically published where the host filesystem permits.
- **FR-004**: Output names MUST use the validated artifact type, remain under the selected root, and resolve collisions deterministically.
- **FR-005**: The system MUST reject unsafe input/output/workspace/database path relationships unless the user explicitly accepts the documented risk.
- **FR-006**: Symlinks, reparse points, inaccessible files, changing inputs, sparse files, and path-length failures MUST have explicit fail-closed behavior and evidence.
- **FR-007**: Users MUST be able to configure limits for source bytes, scanned bytes, candidates, candidate bytes, decoder time, tool output, decompressed bytes, archive members, nesting depth, artifacts, total output bytes, and workers.
- **FR-008**: Each limit MUST have a conservative default and MUST stop only the affected bounded operation unless run integrity is compromised.
- **FR-009**: Candidate work MUST be represented lazily whenever possible so large source ranges are not copied until an operation requires materialization.
- **FR-010**: Every external process MUST use one bounded execution policy covering timeout, cancellation, output capture, process-tree termination, tool identity, cleanup, and structured errors.
- **FR-011**: The application MUST support cancellation at safe checkpoints and bounded parallel processing.

#### Run Lifecycle, Evidence, And Outcomes

- **FR-012**: Runs MUST persist created, running, completed, partial, cancelled, and failed states with start/end timestamps and fatal-error details.
- **FR-013**: File results MUST be committed independently or in bounded batches so one failure does not erase prior evidence.
- **FR-014**: Interrupted runs MUST be resumable using stable source identity, effective configuration, and explicit changed-input policy.
- **FR-015**: The evidence store MUST use an explicit schema version and deterministic forward migrations.
- **FR-016**: Every effective option, application version, platform fact, and external-tool version used by a run MUST be recorded.
- **FR-017**: Artifacts MUST distinguish repaired originals, normalized files, extracted content, previews, frames, raw fragments, and diagnostics.
- **FR-018**: Every artifact MUST link to its source, candidate plan, transformations, validator outcomes, hashes, fidelity grade, and tool evidence.
- **FR-019**: Identical candidate payloads MUST be deduplicated by content identity while preserving all strategy provenance.
- **FR-020**: Human progress, machine-readable event output, and final manifests MUST be separate and deterministic.
- **FR-021**: Fatal runs MUST return non-zero status; partial-recovery status MUST follow an explicit selectable policy.
- **FR-022**: Recovery outcomes MUST distinguish validated original format, validated normalized output, partial content, preview only, unavailable dependency, budget exceeded, cancelled, and failed.

#### Handler And Capability Contracts

- **FR-023**: Every public format MUST be registered through one handler contract that declares detection, inspection, validation, repair, normalization, extraction, preview, tools, encryption behavior, default limits, outputs, and fidelity guarantees.
- **FR-024**: The CLI MUST expose human-readable and machine-readable capability manifests generated from registered handlers.
- **FR-025**: Capability publication MUST fail its quality gate when an advertised operation lacks executable validation evidence.
- **FR-026**: Users MUST be able to request repair, normalize, extract, preview, or carve goals without silent substitution.
- **FR-027**: Scan MUST inventory and detect; classify MUST add classification; recover MUST execute requested goals. Their behavior and evidence MUST remain distinct.
- **FR-028**: Signature, structural, extension, and tool evidence MUST remain distinct so ambiguous and polyglot inputs can be reported honestly.

#### Text And Structured Text

- **FR-029**: Text handlers MUST recognize UTF-8, UTF-16, UTF-32, byte-order marks, Windows-1252, and ISO-8859-1 with confidence and byte-offset evidence.
- **FR-030**: Text recovery MUST preserve valid byte ranges, identify undecodable or binary spans, and MUST NOT invent missing language.
- **FR-031**: Text artifacts MUST include an offset map from recovered ranges and replacements to source bytes.
- **FR-032**: Structured text MUST provide bounded diagnostics without semantic rewriting: JSON and XML parser results, CSV dialect/row-shape results, HTML tag/active-content results, and Markdown fence/link/heading results.
- **FR-033**: Newline or encoding normalization MUST be optional and emitted as a derived artifact separate from byte-preserving recovery.

#### ZIP, TAR, And Package Documents

- **FR-034**: ZIP handling MUST validate end records, directory entries, local headers, descriptors, methods, sizes, and checksums under explicit budgets.
- **FR-035**: When directory metadata is missing, the system MUST be able to scan local members and reconstruct only unambiguous entries into a new archive.
- **FR-036**: Archive extraction MUST enforce path containment, link/device rejection, duplicate-name policy, member limits, ratio limits, decompressed-byte limits, and recursion limits.
- **FR-037**: TAR handling MUST validate sequential headers and checksums and salvage later valid members when earlier regions are damaged.
- **FR-038**: Open XML and OpenDocument handling MUST detect package type independently of suffix and validate required parts, manifests, content types, and relationships.
- **FR-039**: Package repair MUST regenerate metadata only when unambiguous and MUST otherwise emit separately graded text, worksheet, slide, media, attachment, and diagnostic artifacts.
- **FR-040**: Macros, scripts, and embedded executables MUST never run; they may only be preserved or extracted as inert content with warnings.
- **FR-041**: Encrypted and password-protected containers MUST be reported explicitly and MUST NOT trigger password cracking.

#### PDF

- **FR-042**: PDF handling MUST analyze headers, objects, streams, cross-references, trailers, start references, end markers, page trees, and embedded artifacts using bounded reads.
- **FR-043**: PDF repair MAY reconstruct object references only from discovered objects and MUST preserve all warnings and uncertainty.
- **FR-044**: PDF pages, text, images, attachments, and metadata MUST be eligible for separately graded extraction when full document validation fails.
- **FR-045**: Optional PDF tools and renderers MUST run through the same bounded external-process policy and MUST not be required for core inspection.

#### Images

- **FR-046**: PNG handling MUST validate chunk ordering, lengths, checksums, required headers, image-data continuity, end markers, and decompression budgets.
- **FR-047**: GIF handling MUST validate screen descriptors, color tables, extension and image blocks, frames, and trailers while preserving animation when recoverable.
- **FR-048**: BMP handling MUST validate and conservatively repair file/DIB sizes and pixel offsets under raster-size budgets.
- **FR-049**: RIFF-based handling MUST validate container sizes, chunk boundaries, padding, subtype, and recoverable chunks for WebP and AVI.
- **FR-050**: TIFF handling MUST validate byte order, directory chains, offsets, strips, and tiles while detecting cycles and oversized ranges.
- **FR-051**: HEIF, AVIF, JPEG 2000, and RAW handlers MUST expose codec-dependent detection, inspection, preview, extraction, and writing availability separately.
- **FR-052**: Multi-frame and multipage loss MUST never be labeled full recovery.

#### Video, Audio, And Complex Formats

- **FR-053**: MP4/MOV handling MUST scan boxes, validate sizes, report fragmented media and sample-table availability, and expose bounded carving/remux paths.
- **FR-054**: Matroska/WebM, AVI, MPEG transport/program streams, FLV, and ASF handling MUST provide bounded structural diagnostics and format-appropriate resynchronization or carving where defensible.
- **FR-055**: Media validation MUST record streams, duration/timestamp continuity, decoded coverage, warnings, and output fidelity rather than decoder acceptance alone.
- **FR-056**: WAV, MP3, FLAC, AAC, and Ogg handlers MUST support detection and bounded inspection, plus extraction or normalization when an available validator confirms the result.
- **FR-057**: 7z, RAR, and legacy Office support MUST use isolated optional-tool adapters initially, with explicit tool-absent, encryption, multi-volume, solid-archive, macro, and conversion outcomes.

#### Quality, Packaging, And Governance

- **FR-058**: One authoritative version MUST drive package metadata and runtime version reporting.
- **FR-059**: Development and test dependencies MUST be declared separately from runtime dependencies.
- **FR-060**: Automated quality gates MUST cover supported language versions, Windows and Linux, optional tools present and absent, packaging, capability consistency, and documentation links.
- **FR-061**: A license-safe fixture and mutation system MUST cover valid, head/tail truncation, prefixed/suffixed garbage, bit flips, missing indexes, wrong suffixes, empty input, oversized declarations, path attacks, and resource attacks for each public family as applicable.
- **FR-062**: Repeated recovery with the same source, configuration, and tool identities MUST produce the same candidate order, selected artifact identity, and manifest ordering.
- **FR-063**: Benchmark reports MUST measure success and partial-success rates, false positives, content fidelity, runtime, peak memory, output expansion, crashes, timeouts, and budget stops.
- **FR-064**: Public documentation and the machine-readable index MUST be updated from or checked against executable capabilities and current verification evidence.
- **FR-065**: Reports and machine events MUST support deterministic path redaction or pseudonymization and MUST avoid source-content excerpts unless the user explicitly requests them.
- **FR-066**: External tools MUST run with a temporary working directory and minimal environment; users MUST be able to require an available OS isolation wrapper, in which case the operation fails closed when isolation is unavailable.

### Key Entities

- **Run**: A durable recovery session with lifecycle, configuration, environment, tool identities, progress, and final status.
- **Source Asset**: Immutable input identity including normalized path, size, timestamps, hashes, and change-detection evidence.
- **Byte Source**: A bounded random-access and streaming view over source or temporary material.
- **Format Handler**: A declared set of format evidence, supported goals, limits, dependencies, planners, validators, and output guarantees.
- **Capability Record**: The public operation matrix and evidence status for one format family or variant.
- **Candidate Plan**: A lazy, deterministic sequence of source slices and transformations with provenance and estimated resource cost.
- **Attempt**: Execution and validation evidence for a candidate under a particular goal and budget.
- **Artifact**: A published file or diagnostic product with kind, media type, fidelity grade, hashes, source relations, and validator results.
- **Artifact Relation**: A directed provenance edge between sources, candidates, artifacts, previews, members, pages, streams, and diagnostics.
- **Resource Budget**: Per-operation and cumulative limits with consumption and stop reasons.
- **Tool Record**: Availability, resolved identity, version, command policy, duration, output bounds, and exit evidence for an external adapter.
- **Text Span Map**: A mapping between source byte ranges and recovered or replacement text ranges.
- **Archive Member**: A contained member identity with path, method, sizes, checksum, encryption, safety decision, and artifact relation.
- **Document Part**: A package or PDF component with type, relationships, validation state, and recoverability.
- **Media Stream**: An image frame, page, video/audio stream, timing range, or extracted representation with continuity and fidelity evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All automated tests pass from a clean development installation without undeclared test packages.
- **SC-002**: The quality workflow defines jobs for every supported language version, Windows and Linux, and both optional-media-tool states.
- **SC-003**: In the safety fixture suite, 100% of originals and pre-existing outputs retain their original hashes unless explicit replacement is selected.
- **SC-004**: In traversal, link, device, collision, and recursive-container fixtures, 0 artifacts are published outside the chosen output root.
- **SC-005**: Every resource-attack fixture stops at or before its configured count, byte, time, depth, or worker limit and records the triggering limit.
- **SC-006**: Cancellation and resume scenarios complete without orphan processes or temporary published artifacts, and all completed files retain durable evidence.
- **SC-007**: Two identical runs produce identical ordered manifests and selected artifact hashes for all deterministic fixtures.
- **SC-008**: Every public format has a capability record, and 100% of advertised operations link to at least one passing validation scenario or are marked unavailable/experimental.
- **SC-009**: Every required mutation class applicable to a public format has at least one deterministic fixture, and the suite reports coverage gaps as failures.
- **SC-010**: Valid inputs for every natively supported format are accepted without destructive rewriting and with correct artifact suffixes and media types.
- **SC-011**: Partial text recovery maps 100% of emitted text and replacement spans back to explicit source byte ranges.
- **SC-012**: Archive and package safety fixtures produce zero path escapes and stay within configured member, depth, expansion, and output limits.
- **SC-013**: Full-package, repaired, normalized, partial-content, preview-only, unavailable, budget-exceeded, cancelled, and failed outcomes are distinguishable in both human and machine-readable reports.
- **SC-014**: Fatal CLI scenarios return non-zero status, while successful, partial, and no-recovery outcomes follow their documented selectable exit policy.
- **SC-015**: Benchmark output includes recovery, fidelity, performance, memory, expansion, crash, timeout, and budget metrics for every executed fixture group.
- **SC-016**: The complete non-optional local test suite finishes within 180 seconds on a typical development workstation using the bundled synthetic corpus.
- **SC-017**: Peak process memory for streaming inspection of a 1 GiB sparse or generated fixture remains below 256 MiB, excluding explicitly materialized bounded tool inputs.
- **SC-018**: Public documentation, CLI help, capability manifests, version reporting, and package metadata contain no known contradictory support or version claims.
- **SC-019**: With path redaction selected, generated JSON, JSONL, CSV, and text reports contain zero canonical source or workspace paths while retaining stable per-run source identities.
- **SC-020**: With required tool isolation selected, 100% of tool operations either run through a recorded isolation wrapper or fail before launching the external decoder.

## Assumptions

- "Implement all" means every roadmap family receives the strongest bounded and honestly graded capability described here; it does not mean impossible reconstruction of missing semantic content.
- The application remains offline-first and local-only, with no service, account, or cloud dependency.
- Existing JPEG behavior remains available unless a safety or correctness requirement explicitly changes it.
- Optional external tools may improve recovery, but native inspection and tool-unavailable reporting remain usable without them.
- Password cracking, macro execution, active-content execution, malware analysis, and bypass of encryption are outside scope.
- Proprietary, encrypted, multi-volume, solid, vendor-specific, or heavily damaged formats may support detection, inspection, preview, extraction, or adapter-based conversion without claiming full repair.
- Test fixtures may be generated synthetically or derived from redistribution-safe assets; private user documents are not added to the repository.
- No commit, push, branch mutation, release, or deployment is implied by implementation.
