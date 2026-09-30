# Security And Local Data Handling

File Uncorrupter is offline-first. Current source defines no network calls, telemetry upload, HTTP server, authentication layer, or authorization layer.

GitHub-facing reporting guidance is in [../../SECURITY.md](../../SECURITY.md).

## Security Support And Reporting

The repository does not currently publish a supported-version matrix or GitHub releases.

- Do not publish exploit details, credentials, private media, private paths, or other sensitive evidence in public Issues or pull requests.
- Non-sensitive security hardening and reproducible security defects may be discussed through GitHub Issues.
- No dedicated private security mailbox or other private reporting route is documented in the repository. If private disclosure is required, use an existing private channel to the repository owner rather than posting sensitive details publicly.
- No bug bounty, response-time guarantee, or coordinated-disclosure timeline is promised.

## Source Evidence And Output Separation

The CLI reads from `input_root` and can write recovered artifacts, SQLite state, reports, raw candidates, and workspace/config snapshots.

Operational requirement:

- keep original evidence read-only where possible
- use separate output, database, report, raw-candidate, and workspace locations
- do not point generated paths into source evidence trees

Do not assume current code prevents every unsafe path alias/overlap. Enforcement work is tracked separately in the GitHub work ledger.

## Untrusted Media

Inputs are arbitrary binary media files. Treat them as hostile:

- run recovery as a non-privileged user
- use a dedicated working directory
- keep decoder tooling updated
- isolate especially hostile samples where practical
- review recovered artifacts before opening or sharing them

## Decoder Subprocesses

When available, [decoders.py](../../src/file_uncorrupter/decoders.py) invokes `ffmpeg` and `ffprobe` through `subprocess.run()` with timeouts on multiple paths.

FFmpeg/ffprobe materially expand the parser attack surface. Do not interpret subprocess use as a sandbox: the current repository does not implement process sandboxing or privilege isolation.

## Resource Boundaries

The project has some subprocess timeouts and a candidate-count option, but current behavior must not be described as fully resource-bounded. Large or pathological inputs can still consume substantial memory/CPU/disk, and current open work includes stronger resource and timeout containment.

Use constrained working environments for hostile corpora.

## Evidence And Privacy

SQLite databases and generated reports can include:

- local input/output paths
- file hashes
- signature offsets
- classification evidence
- decoder errors
- media dimensions, duration, and frame counts
- recovery strategy/candidate identifiers

These artifacts are not anonymized. Scrub sensitive information before sharing.

## Credential And Secret Handling

The project does not require repository-stored credentials for its current CLI behavior.

Do not commit:

- passwords, API keys, tokens, private keys, certificates, or `.env` contents
- private URLs or account identifiers
- private media or private filesystem paths in documentation/reports

## Not Currently Provided

Do not assume the project provides:

- encryption at rest
- secure deletion
- role-based access control
- remote API hardening
- decoder sandboxing
- privacy scrubbing/anonymization
- production deployment security
- complete hostile-input resource containment

Add or document those properties only when current source and verification establish them.
