<!-- codex-memory-scaffold:security-model -->
# Security Model

## Verifiable Security Signals
- Security-relevant doc: [docs/security-model.md](security-model.md)
- Security-relevant doc: [docs/security/SECURITY.md](security/SECURITY.md)

## Sensitive Data Handling
- Do not copy secrets, credentials, private keys, tokens, private certificates, production config, or .env contents into Obsidian notes.
- Environment files other than documented examples were not read during scaffolding.
- Generated dependency folders and build outputs should stay outside project memory notes unless a maintainer explicitly asks to document them.

## Unknowns
- Confirm authentication, authorization, data classification, and deployment trust boundaries from current source/docs before making security claims.
