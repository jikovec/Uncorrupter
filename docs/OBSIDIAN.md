# Obsidian Local Vault Guide

Tags: #obsidian/local #obsidian/graph #repo/index

This repository can be opened as a local Obsidian vault for documentation, project memory, reports, and handoff context. Obsidian is only a local reading and navigation layer for this repo. It is not part of the runtime product.

## Start Here

- [Root vault index](../00_Index.md)
- [Documentation index](INDEX.md)
- [Agent orientation](AGENT-INDEX.md)
- [Source map](SOURCE-MAP.md)
- [Connection map](CONNECTIONS.md)
- [Root reports index](../reports/INDEX.md)
- [Root handoffs index](../handoffs/INDEX.md)

Useful Obsidian targets:

- [[00_Index|Root vault index]]
- [[docs/INDEX|Documentation index]]
- [[docs/AGENT-INDEX|Agent orientation]]
- [[docs/SOURCE-MAP|Source map]]
- [[docs/CONNECTIONS|Connection map]]

## Local-First Rules

- Keep the vault local-first and plaintext.
- Keep `.obsidian/` ignored. It can contain private workspace state, graph settings, local plugin state, and window layout.
- Do not add Obsidian Sync, cloud sharing, account coupling, encryption setup, or company integrations.
- Do not commit secrets, credentials, private keys, tokens, account IDs, private URLs, private certificates, or `.env` contents into notes.
- Do not use Obsidian notes to store generated dependency folders, build output, recovery output, SQLite databases, or private media paths.

## Markdown And Link Conventions

- Prefer normal Markdown links for canonical documentation because they work on GitHub and in code review.
- Use wiki links only in hub notes where Obsidian backlinks and graph navigation are useful.
- When a note needs to be both GitHub-readable and Obsidian-friendly, include a normal Markdown link first and a wiki link only if it adds value.
- Keep links repo-relative. Do not write machine-specific absolute paths into docs.
- Do not rename or move existing docs unless a future task explicitly allows it.

## Graph Hubs

Use these notes as graph hubs:

- `00_Index.md` - root vault entry point.
- `docs/INDEX.md` - current documentation entry point.
- `docs/AGENT-INDEX.md` - future-agent orientation.
- `docs/SOURCE-MAP.md` - source and tests by subsystem.
- `docs/CONNECTIONS.md` - cross-links among docs, source, tests, reports, and handoffs.
- `reports/INDEX.md` - workflow reports and implementation evidence.
- `handoffs/INDEX.md` - deferred work and next-agent notes.

## Tag Taxonomy

Global tags:

- `#repo/index`
- `#repo/architecture`
- `#repo/development`
- `#repo/testing`
- `#repo/security`
- `#repo/roadmap`
- `#repo/decision`
- `#repo/source-map`
- `#repo/connection-map`
- `#agent/orientation`
- `#agent/handoff`
- `#agent/report`
- `#obsidian/local`
- `#obsidian/graph`

Repo-specific tags:

- `#uncorrupter/cli`
- `#uncorrupter/recovery`
- `#uncorrupter/jpeg`
- `#uncorrupter/video`
- `#uncorrupter/ffmpeg`
- `#uncorrupter/sqlite`
- `#uncorrupter/evidence`
- `#uncorrupter/signature-detection`
- `#uncorrupter/testing`
- `#uncorrupter/history`
- `#uncorrupter/release-artifacts`

Tag only hub pages, reports, handoffs, and durable decision notes. Avoid tagging every implementation detail.

Do not use these tags unless future source/docs implement the matching behavior:

- `#repo/cloud`
- `#repo/auth`
- `#repo/encryption`
- `#repo/telemetry`
- `#repo/production-deploy`

## Privacy And Safety

Obsidian settings and plugins can store local state that does not belong in the repository. Keep `.obsidian/` ignored unless a future explicit decision says otherwise.

File Uncorrupter handles untrusted media and can produce reports containing filenames, paths, hashes, decoder errors, and media metadata. Treat recovery outputs, SQLite databases, JSON reports, CSV reports, and raw candidates as local evidence, not anonymized public artifacts.
