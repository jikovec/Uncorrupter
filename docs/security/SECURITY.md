# Security And Local Data Handling

File Uncorrupter is offline-first. The current repo does not define network calls, telemetry uploads, an HTTP server, authentication, or authorization.

Related docs:

- [Obsidian local vault guide](../OBSIDIAN.md)
- [Agent orientation](../AGENT-INDEX.md)
- [Connection map](../CONNECTIONS.md)

## Local File Access

The CLI reads files from the selected `input_root` and writes outputs to the selected output directory, database path, and workspace path. Use separate output directories so recovered artifacts, raw candidates, and generated databases do not overwrite original evidence.

The recovery pipeline records local file paths, SHA-256 hashes, classification evidence, decoder errors, and output metadata in SQLite.

## Untrusted Media

Inputs are arbitrary binary media files. Treat them as untrusted:

- run recovery in a dedicated working directory
- keep original files read-only when possible
- keep recovered outputs separate from originals
- avoid opening recovered artifacts in privileged applications

## Decoder Subprocesses

When `ffmpeg` and `ffprobe` are available, [src/file_uncorrupter/decoders.py](../../src/file_uncorrupter/decoders.py) invokes them through `subprocess.run()` with timeouts. FFmpeg is optional but materially changes the attack surface because it parses untrusted media in a separate local process.

Practical controls:

- keep FFmpeg updated
- run the tool as a non-administrator user
- process hostile samples in an isolated workspace
- review generated outputs before sharing them

## Evidence And Privacy

The SQLite database and reports can include:

- input and output paths
- media dimensions
- duration and frame counts
- decoder errors
- signature offsets
- SHA-256 hashes
- recovery strategy IDs

Do not treat reports as anonymized. They may reveal filenames, directory structure, and properties of recovered files.

## Not Currently Provided

The current repo does not implement:

- encryption at rest
- secure deletion
- role-based access control
- remote API hardening
- sandboxing for decoder subprocesses
- privacy scrubbing of generated reports

If those properties are required, add them as explicit product work rather than assuming the current CLI provides them.

## Obsidian And Documentation Privacy

The repo root can be opened as a local Obsidian vault for documentation. Keep `.obsidian/` ignored because it can contain private workspace state, graph settings, local plugin state, and window layout.

Do not copy secrets, credentials, account identifiers, private URLs, private media paths, or `.env` contents into documentation, reports, handoffs, or `docs/agent-index.json`.
