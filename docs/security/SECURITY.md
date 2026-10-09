# Security And Local Data Handling

File Uncorrupter processes malformed, potentially hostile files. Its security model is local, defensive, bounded, and evidence preserving. The current implementation reduces common file-recovery risks; it is not a formal sandbox, malware scanner, content-disarm product, or security certification.

## Threat Model

In scope:

- malformed lengths, offsets, checksums, indexes, and container graphs;
- decompression and member-count attacks;
- path traversal, absolute paths, Windows drive/UNC forms, links, devices, and duplicate archive members;
- huge inputs, large candidates, excessive artifacts, runaway output, and decoder timeouts;
- symlink/reparse intake and source replacement/change during a run;
- parser/tool crashes, hangs, large stdout/stderr, child processes, and inherited environment secrets;
- macros, scripts, document relationships, embedded objects, HTML active elements, and media metadata;
- encrypted, solid, and multivolume container ambiguity;
- sensitive local paths and recovery metadata in reports.

Not solved by the current implementation:

- kernel/codec/parser zero-days;
- hostile native-library behavior inside the Python process, including Pillow codecs;
- a bundled OS/container/VM sandbox;
- malware detection or safe opening of recovered artifacts;
- password recovery, key management, or encryption bypass;
- guaranteed secure deletion of temporary/storage media;
- protection after a user opens recovered active content in another application;
- a comprehensive adversarial fuzzing or independent security audit.

## Input Immutability

- Recovery never intentionally writes through an input path.
- `FileByteSource` resolves a regular file, rejects symlinks/reparse points, records identity, and rechecks identity around reads.
- Intake uses stable traversal and prunes link/reparse entries.
- Source changes produce explicit evidence and stop affected processing.
- Source hashes are streamed; accepted source size does not authorize the same size in-memory materialization.

For irreplaceable evidence, use a copy or read-only mount/device anyway. Application checks are not a substitute for filesystem write protection.

## Layout And Output Controls

Before creating run state, the CLI checks unsafe relationships among:

- input root;
- output root;
- workspace root;
- SQLite database;
- event/report destinations where applicable.

Normal recovery requires separation. `--allow-risky-layout` accepts only the documented overlap risk; it does not disable safe relative names, artifact containment, source immutability, or archive protections.

Artifacts:

- are resolved beneath an approved root;
- reject traversal, absolute, drive, UNC, and reserved unsafe forms;
- use temporary siblings;
- are flushed and atomically published where supported;
- preserve existing destinations by default;
- clean incomplete temporary siblings;
- consume artifact-count/output-byte budgets before final publication.

Atomic rename behavior depends on the host filesystem. Network/removable filesystems can provide weaker durability semantics than local NTFS/ext4-like storage; the artifact records whether publication was reported atomic.

## Resource Controls

Configurable limits cover:

- source and scanned bytes;
- materialized and candidate bytes/count;
- decoder/tool duration and captured output;
- archive member count/size, expanded bytes, ratio, and nesting depth;
- artifact count and total output bytes;
- worker count.

Budgets are hierarchical and thread-safe. A limit fails before the over-limit consume/publish action and records the triggering name, limit, and attempted total. Partial artifacts already safely published are preserved and labeled; the source remains unchanged.

Limits reduce denial-of-service risk but do not prove bounded peak memory in every third-party codec. The benchmark now samples main-process RSS, but explicitly excludes FFmpeg, qpdf, 7-Zip, LibreOffice, isolation wrappers, and other child-process memory. Pillow and other in-process codecs may allocate decoded rasters/frames beyond Python-level `tracemalloc` observations; process-tree and OS-enforced memory limits remain future hardening.

## Archive And Package Safety

- ZIP/TAR paths are normalized and contained.
- Valid ZIP/TAR and package-document paths stream through the immutable seekable source instead of requiring a source-sized memory copy.
- Symlinks, hard links, devices, and unsupported special members are rejected.
- Duplicate output names are not silently overwritten.
- CRC/size/expansion/member/depth checks apply before extraction.
- ZIP reconstruction uses only unambiguous validated local members.
- TAR reconstruction occurs only after structural damage/resynchronization; a valid TAR is not needlessly rewritten.
- Open XML/OpenDocument macros, external relationships, scripts, and embedded executables are evidence/inert bytes, never executed.
- Encrypted members/packages are reported. Password guessing is outside scope.

Do not open extracted documents, HTML, scripts, or binaries on a trusted workstation merely because extraction succeeded.

## Structured Text And Active Content

Text recovery decodes bytes and emits provenance spans. It does not evaluate JSON/XML/HTML/Markdown or execute links/scripts. HTML active elements/attributes are counted as warnings. Invalid JSON/XML/CSV/Markdown is graded partial even if its bytes decode without loss.

RTF control words are stripped for an inert partial text view. RTF objects and legacy Office OLE content are never executed. When LibreOffice is available, the only public legacy Office conversion is a headless, bounded, private-profile PDF preview; the exact PDF is natively validated before atomic publication and remains labeled `preview_only`.

## Image And Media Boundary

Native parsers validate only the structures they explicitly implement. Pillow and optional media codecs parse untrusted bytes inside the current local process unless an external isolation wrapper surrounds the entire application.

When FFmpeg and ffprobe are both available, the public media handler advertises copy-remux normalization, per-stream extraction, and one-frame preview. The exact temporary output is independently probed and hashed before it is streamed through atomic publication, and the published hash must match the validated hash. These checks establish bounded parser/output evidence; they do not make FFmpeg a sandbox or prove that missing media was reconstructed.

## External Process Boundary

Supported external processes use:

- an argument vector with no shell string;
- executable resolution and version evidence;
- a minimal allowlisted environment;
- a temporary working directory;
- a timeout and cancellation token;
- bounded combined output capture;
- process-tree termination and cleanup evidence;
- structured errors.

`--require-tool-isolation --isolation-wrapper ...` adds a run-wide wrapper requirement. If the wrapper is missing, no wrapped tool launches. The wrapper must be supplied and trusted by the user; File Uncorrupter does not install or configure one.

Tool availability does not grant authority to upload, publish, buy services, or process files outside the selected local scope.

## Evidence, Reports, And Privacy

SQLite, JSONL, manifests, CSV, text reports, and recovery artifacts can reveal:

- source filenames and local paths;
- file sizes, hashes, classifications, and failure details;
- archive/document member names;
- tool paths/versions;
- extracted user content in artifact files.

They are not anonymized public artifacts.

`--redact-paths` pseudonymizes configured roots with a deterministic salted ID. Choose a private `--redaction-salt` if correlation resistance matters, but do not place secrets on a shared command line. Redaction does not remove hashes, member names, diagnostics, or artifact content. Review every report before sharing.

The persistence serializer avoids raw byte payloads: bytes are represented by length and SHA-256 evidence. Reports avoid source-content excerpts by default.

## Local Project Privacy

- `.obsidian/` is ignored local editor state; no cloud sync/account/encryption setup is part of the project.
- `.agents/` and `.specify/` are local workflow scaffolding.
- `.uncorrupter-workspace/`, databases, events, reports, recovered output, and sample inputs should remain private unless explicitly reviewed.
- Secrets, `.env` contents, credentials, tokens, cookies, keys, and private URLs must not be added to fixtures, reports, docs, or commits.

## Safe Operating Recommendations

1. Work on a copy or read-only source.
2. Use a new empty output root and a separate workspace/database location.
3. Run `capabilities --format json` and disable unneeded optional tools.
4. Begin with low resource limits and one worker for unknown hostile files.
5. Use an OS sandbox/VM/container appropriate to the codecs/tools when risk is high.
6. Keep network access disabled for recovery where feasible.
7. Inspect diagnostics and hashes before opening an artifact.
8. Scan artifacts with appropriate security tooling before native-app use.
9. Keep reports and extracted data private.
10. Treat partial/preview results as evidence, not a clean-file guarantee.

## Reporting Security Issues

This repository does not currently document a dedicated private vulnerability intake channel. Do not publish exploit samples, secrets, or private user files in a public issue. Coordinate a private maintainer channel first; if none exists, disclose only a minimal sanitized description until a private path is established.
