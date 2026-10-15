# Data Model: Stabilized Multi-Format Recovery

## Run

Fields:

- id
- command
- state: created, running, completed, partial, cancelled, failed
- input_root, output_root, workspace_root, database_path
- engine or handler selection
- recovery goals
- overwrite and partial-exit policies
- effective configuration and limits
- application, platform, and tool snapshots
- created_at, started_at, finished_at
- resume_of_run_id
- cancellation reason and fatal error

State transitions:

- created to running
- running to completed, partial, cancelled, or failed
- cancelled, partial, or failed to a new resumed run linked by resume_of_run_id
- terminal runs never return to running

## Source Asset

Fields:

- run_id and file_id
- relative and absolute paths
- size, modification time, filesystem identity where available
- streaming SHA-256
- declared suffix and detected family evidence
- status: discovered, scanned, classified, processing, recovered, partial, skipped, unavailable, budget_exceeded, cancelled, failed
- started_at, finished_at, error code and detail

Validation:

- relative path must remain under the canonical input root
- identity must be rechecked before publication and resume reuse

## Resource Limits And Budget Events

Limits:

- maximum source bytes
- maximum scanned bytes per source
- maximum candidates and candidate bytes
- maximum decoder and tool time
- maximum captured tool-output bytes
- maximum archive members, member bytes, total decompressed bytes, ratio, and depth
- maximum artifacts and output bytes
- maximum workers

Budget event fields:

- run/file/attempt scope
- budget name
- configured limit
- consumed amount
- outcome and timestamp

## Capability Record

Fields:

- family and variants
- extensions and signatures
- detect, inspect, validate, repair, normalize, extract, preview, and carve levels
- required and optional tools
- encryption and active-content behavior
- default limits
- output kinds and fidelity guarantees
- tested fixture identifiers
- availability and unavailable reasons

## Candidate Plan

Fields:

- stable plan identity
- handler and strategy
- family and goal
- priority
- ordered source slices and transformations
- estimated input, materialization, and output costs
- provenance and diagnostic metadata
- payload hash after materialization

Rules:

- ordering is deterministic
- equal payload hashes share validation work while retaining strategy links
- a plan cannot materialize beyond its active budget

## Attempt

Fields:

- candidate and file identity
- phase and validator/adapter
- start/end time and duration
- success state and outcome grade
- structural, decoder, fidelity, and continuity evidence
- resource consumption
- tool record
- structured error

## Artifact

Fields:

- stable artifact identity
- kind: repaired, normalized, extracted, preview, frame, raw_fragment, diagnostics, manifest
- relative output path and media type
- size and SHA-256
- fidelity grade
- validation state and validators
- atomic publication state
- width, height, duration, frames, pages, members, or streams where applicable
- metadata and warnings

## Artifact Relation

Fields:

- parent kind and identifier
- child artifact identifier
- relation type: derived_from, extracted_from, preview_of, frame_of, member_of, page_of, stream_of, validates, supersedes
- source byte range or document/container locator
- transformation and ordering metadata

## Text Span Map

Fields:

- artifact identity
- source byte start/end
- output character start/end
- encoding
- span type: exact, replacement, skipped_binary, normalized_newline
- confidence and diagnostic

## Archive Member

Fields:

- source/container identity
- original and safe names
- header offset
- method and flags
- compressed and uncompressed sizes
- checksum/CRC and validation state
- encryption, directory, link, device, duplicate, and containment flags
- extraction outcome and artifact identity

## Document Part

Fields:

- package or PDF identity
- part/object locator and media type
- required, present, parsed, encrypted, macro, active-content, orphan, and missing flags
- relationships or object references
- extraction artifact and validation warnings

## Media Stream

Fields:

- source/container identity
- stream or frame index
- codec, type, dimensions, rate, duration, timestamps
- continuity, decoded coverage, keyframe, animation, or multipage evidence
- extracted or preview artifact identity

## Tool Record

Fields:

- logical tool name
- resolved executable path and version
- availability
- command policy identifier
- exit code, timeout, cancellation, duration
- captured output hashes and bounded excerpts
- cleanup status
