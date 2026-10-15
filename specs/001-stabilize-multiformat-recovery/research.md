# Research: Stabilized Multi-Format Recovery

## Decision 1: Keep The Runtime Dependency Surface Small

**Decision**: Keep Pillow mandatory and implement shared safety, persistence, text, ZIP, TAR, XML, JSON, CSV, hashing, and process control with the Python standard library. Treat FFmpeg/ffprobe, qpdf, 7z, unrar, and LibreOffice as optional adapters discovered at runtime.

**Rationale**: The application is offline-first and must remain installable without a large native dependency chain. Optional tools can add depth without turning their absence into a fatal package failure.

**Alternatives considered**: Add document, PDF, archive, and media libraries as mandatory dependencies; rejected because installability and attack surface would grow before the core safety model was stable.

## Decision 2: Use Explicit Bounded Byte Sources

**Decision**: Use seekable file-backed byte sources with bounded reads, streaming iteration, and streaming hashes. Candidate plans reference source ranges and small transforms; materialization is budgeted.

**Rationale**: Current whole-file bytes scale poorly and create duplicate payloads. File-backed sources preserve random access needed by damaged container analysis while keeping memory bounded.

**Alternatives considered**: Memory mapping all files; rejected as the default because address-space behavior, changing files, sparse files, and cleanup are harder to reason about cross-platform. Streaming-only readers; rejected because many damaged formats require random access.

## Decision 3: Publish Through Atomic No-Clobber Writers

**Decision**: Default to no-clobber, validate final type and content before publication, flush temporary siblings, and atomically publish. Replacement is an explicit policy; deterministic suffixing is a separate policy. Reports support deterministic path pseudonyms.

**Rationale**: Recovery software must not destroy originals or earlier results. Temporary siblings keep rename atomic on the same filesystem.

**Alternatives considered**: Direct writes and overwrite flags passed to decoders; rejected because partial files and races remain possible.

## Decision 4: Inspect Archives Before Extracting

**Decision**: Parse member metadata first, enforce application-level containment and expansion budgets, stream regular members into a fresh temporary tree, and reject links/devices by default.

**Rationale**: Official Python ZIP and TAR guidance warns that untrusted extraction requires prior inspection and additional denial-of-service controls. TAR data filters alone do not enforce all count and byte limits.

**Alternatives considered**: Call extractall with library defaults; rejected because it cannot enforce the complete cross-format collision, expansion, and output policy.

## Decision 5: Build Package Documents On ZIP

**Decision**: Treat Open XML and OpenDocument files as packages whose content type, root relationships, manifests, required main parts, and part graph are validated after ZIP recovery.

**Rationale**: Open XML files are ZIP packages of parts and relationships. Part-level recovery provides useful text/media outcomes even when a fully valid office document cannot be rebuilt.

**Alternatives considered**: Add separate DOCX/XLSX/PPTX libraries first; rejected because they generally assume a valid package and do not solve damaged ZIP reconstruction or shared safety.

## Decision 6: Provide Conservative Native PDF Analysis

**Decision**: Implement bounded header/object/xref/trailer/page-tree diagnostics and conservative reference reconstruction, with optional qpdf validation/repair and optional rendering.

**Rationale**: Object scanning can recover evidence and embedded content without a third-party dependency. qpdf is valuable for damaged cross-reference recovery but must remain an independently recorded adapter, not silent proof of fidelity.

**Alternatives considered**: Treat PDF as text; rejected because streams and object references are binary/container structures. Make qpdf mandatory; rejected for portability.

## Decision 7: Separate Structural Analysis From Decoder Acceptance

**Decision**: Native image/media analyzers report structure and continuity; Pillow and FFmpeg validate or derive artifacts through bounded adapters. Outcomes grade full recovery, normalization, partial extraction, and preview separately.

**Rationale**: A decoder opening one frame does not prove animation, pages, streams, timestamps, or full content survived.

**Alternatives considered**: Use decoder success as the only validator; rejected because it caused current fidelity overstatement.

## Decision 8: Version The Evidence Schema

**Decision**: Introduce a schema_meta table and ordered migrations. Add lifecycle, file status, source identity, capability/tool snapshots, artifact relations, budget events, and machine events without deleting historical tables.

**Rationale**: Existing databases must remain readable and long runs need durable progress. Additive migration minimizes risk.

**Alternatives considered**: Continue opportunistic column checks; rejected because version-dependent behavior becomes implicit and untestable. Replace the database; rejected because historical evidence would be lost.

## Decision 9: Resume By Stable Identity

**Decision**: Resume uses relative path, size, modification time, and content hash. Completed matching files are reused; changed files follow an explicit reject or reprocess policy.

**Rationale**: Paths alone are not identity. Hashes alone require a full read but can be computed streaming and are necessary for evidence integrity.

**Alternatives considered**: Resume by path only; rejected because it could silently attach old recovery results to new bytes.

## Decision 10: Deterministic Bounded Parallelism

**Decision**: Discover and order inputs deterministically, execute file analysis with a bounded worker pool, serialize database publication and event sequence, and sort candidates and artifacts by stable keys.

**Rationale**: Parallelism should improve throughput without changing selected artifacts or manifests.

**Alternatives considered**: Fully concurrent database writes; rejected because it complicates ordering and migrations. Sequential-only operation; rejected because the specification requires bounded parallelism.

## Decision 11: Use One Authoritative Version

**Decision**: Runtime package version is the authoritative attribute and build metadata resolves it dynamically. Development dependencies are declared as a packaging extra.

**Rationale**: This removes the current 0.3.0 versus 0.2.0 contradiction while keeping editable and built installs consistent.

**Alternatives considered**: Duplicate the same literal in two files; rejected because drift remains possible.

## Decision 12: CI Is A Declared Quality Surface

**Decision**: Add Windows and Linux Python 3.11-3.13 jobs, core tool-absent tests, one FFmpeg-present job, packaging validation, capability consistency, and documentation checks.

**Rationale**: Current support is cross-platform and tool-optional but has no automated proof. Official GitHub Actions guidance supports OS/language matrices.

**Alternatives considered**: One Linux job; rejected because path, subprocess, atomic rename, and SQLite behavior are materially platform-sensitive.

## Decision 13: Make Tool Isolation An Explicit Capability

**Decision**: Every external tool receives a fresh temporary working directory and allowlisted environment. A configured OS wrapper may provide stronger isolation; require-isolation mode refuses to launch when none is available.

**Rationale**: Timeouts and process-tree cleanup bound availability failures but are not a sandbox. Explicit policy prevents a best-effort process boundary from being misrepresented as OS isolation.

**Alternatives considered**: Claim subprocess execution alone is sandboxing; rejected as false. Make one platform-specific sandbox mandatory; rejected because the supported Windows/Linux environments do not share one built-in interface.
