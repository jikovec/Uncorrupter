<!-- codex-memory-scaffold:decisions -->
# Decisions

## Active Decisions

The following decisions describe implemented architecture. They do not authorize release, deployment, or remote changes.

### 2026-08-05 - Immutable Evidence And New-Artifacts-Only Recovery

- Context: Damaged inputs may be unique evidence; in-place repair and ambiguous output reuse make failure destructive and provenance weak.
- Decision: Inputs are opened read-only through identity-checked byte sources. Recovery writes only contained, atomic, no-clobber artifacts beneath a separate root.
- Consequences: Users must choose a separate output location. Replacement is not a normal CLI recovery mode. Source drift stops affected work.
- References: `byte_source.py`, `paths.py`, `atomic.py`, `test_safe_recovery.py`.

### 2026-08-05 - Handler Registry And Explicit Goal Semantics

- Context: A single media engine could not express text, archive, package, PDF, extraction, preview, and partial-fidelity boundaries honestly.
- Decision: Each public format variant has one registered handler with capability, inspect, plan, and execute contracts. Repair, normalize, extract, preview, and carve are distinct requests; unsupported goals are not substituted.
- Consequences: Capability output can be generated and tested. New formats must satisfy the common safety/evidence contract.
- References: `handlers/base.py`, `handlers/registry.py`, `capabilities.py`.

### 2026-08-05 - Bounded Optional Tools Through One Process Boundary

- Context: Decoders and archive/document tools may hang, overproduce output, inherit secrets, or outlive cancellation.
- Decision: All supported external execution uses one no-shell runner with a minimal environment, temporary work directory, timeout, output limit, cancellation/tree cleanup, tool identity, and optional required isolation wrapper.
- Consequences: Requiring isolation fails closed. Tool presence alone does not advertise an output goal; exact artifacts still need validation and persistence.
- References: `process_runner.py`, `decoders.py`, `test_process_runner.py`.

### 2026-08-05 - Durable Per-File Evidence And Resume-As-New-Run

- Context: Long recovery runs must retain completed evidence after one file fails or execution is interrupted.
- Decision: SQLite schema version 2 stores lifecycle and typed evidence. File work uses savepoints/independent commits. Resume creates a linked new run; changed inputs follow an explicit policy and reprocessing uses a new output namespace.
- Consequences: Prior evidence is preserved and resumptions are auditable. Config/source identity mismatches cannot be silently reused.
- References: `db.py`, `pipeline.py`, `cli.py`, `test_run_lifecycle.py`.

### 2026-08-05 - Executable Capability Truth And Tool-Disabled Baseline

- Context: Narrative extension lists had drifted beyond the implementation.
- Decision: Handler records generate the capability manifest. The checked-in Markdown baseline is produced with optional external tools disabled and compared byte-for-byte in tests; a live command resolves the current machine.
- Consequences: Conditional tools may broaden live output, but docs retain a reproducible minimum. Any advertised operation needs fixture evidence or the quality gate fails.
- References: `capabilities.py`, `docs/capabilities.generated.md`, `test_capabilities.py`.

### 2026-08-08 - Exact-Artifact Media And Structured-Text Fidelity

- Context: Existing decoder primitives could be mistaken for a complete public FFmpeg artifact path, and lossless byte decoding could hide malformed JSON/XML/CSV/Markdown.
- Decision: Media normalize/extract/preview become public only when both FFmpeg and ffprobe are available. Each exact temporary artifact is independently validated, hash-correlated with its atomic publication, and linked to stream/timing/coverage/tool evidence. Structurally invalid text receives `partial_content` even when original bytes are preserved.
- Consequences: Tool-absent capability remains `none`; tool-present output is still narrowly graded as remux, extracted stream, or preview rather than reconstructed original media. Useful partial bytes remain available without a false validation claim.
- References: `handlers/media.py`, `handlers/text.py`, capability and text tests.

### 2026-08-08 - Streaming Public Paths With Explicit Reconstruction Fallbacks

- Context: A source-size ceiling alone did not prevent accepted ZIP/TAR, package, PDF, TIFF, or media inputs from requiring source-sized Python memory.
- Decision: `FileByteSource` exposes a read-only seekable adapter, and normal public archive/package/PDF/TIFF/media paths use streaming, bounded random access, or direct immutable tool paths. Algorithms that still require complete corrupt-container reconstruction must check and report the materialization limit before reading.
- Consequences: Large valid inputs are no longer rejected merely because `max_materialized_bytes` is smaller than the source. Third-party decoded rasters/frames, corrupt rebuilds, and child tools retain explicitly documented memory/disk boundaries.
- References: `byte_source.py`, format handlers, `decoders.py`, `test_streaming_handlers.py`.

### 2026-08-08 - Labeled Benchmark Metrics, No Self-Declared Ground Truth

- Context: Recovery rates without labels could not establish false-positive, false-negative, or fidelity accuracy, and Python allocation tracing did not represent process memory.
- Decision: Benchmark labels use a versioned, bounded, safe-relative-path JSON file separate from run output. Metrics are global and per group; source hashes can pin identity. RSS is sampled from the main process and explicitly excludes child processes.
- Consequences: Label-dependent fields remain unavailable when labels are absent. Main-process peak RSS is measurable, but whole process-tree memory remains an open gate.
- References: `benchmarking.py`, `cli.py`, `reporting.py`, `docs/BENCHMARK-GROUND-TRUTH.md`, benchmark tests.

## Decision Log
Add future decisions here using this structure:

### YYYY-MM-DD - Decision Title
- Context:
- Decision:
- Consequences:
- References:

## Linked Decision Records
- Add links to ADRs or existing decision files when they are confirmed current.

## Documentation Indexing Notes
- The current agent and Obsidian orientation system uses existing docs rather than creating duplicate uppercase docs such as `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `docs/SECURITY.md`, or `docs/DECISIONS.md`.
- `docs/agent-index.json` is the canonical machine-readable agent index.
- `.agents/index.json` is omitted because `.agents/` is local-only ignored Spec Kit scaffolding in this repo.
- These notes document the current documentation structure; they are not product architecture decisions.
