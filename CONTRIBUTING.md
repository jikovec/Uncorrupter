# Contributing

File Uncorrupter is a small public repository with an issue-and-pull-request workflow. Keep changes source-backed, scoped, and reviewable.

## Before Starting

1. Read [AGENTS.md](AGENTS.md) and [docs/INDEX.md](docs/INDEX.md).
2. Search existing GitHub Issues and pull requests to avoid duplicate or conflicting work.
3. For material work, use an existing issue or create one that states the outcome, evidence, scope, and acceptance criteria.
4. Preserve unrelated local changes and historical evidence.

## Development

Canonical setup and commands are in [docs/setup/DEVELOPMENT.md](docs/setup/DEVELOPMENT.md).

Minimum editable install:

```text
python -m pip install -e .
```

Run the current test suite when applicable and when `pytest` is available:

```text
python -m pytest
```

Documentation/index changes should also run:

```text
python -m json.tool docs/agent-index.json
git diff --check
```

Never report an unavailable or unrun check as passing.

## Branches And Pull Requests

Use the normal flow:

`Issue -> branch -> implementation -> verification -> pull request`

Keep each pull request focused. Describe:

- the linked issue/work object
- what changed and why
- verification actually run
- unavailable or blocked checks
- security/data-handling impact
- intentionally preserved historical/generated artifacts

Do not merge, tag, release, publish, or deploy unless separately authorized.

## Documentation

Update current documentation when behavior, commands, paths, architecture, tests, security boundaries, or work-management rules change. Prefer the existing canonical document instead of creating a competing root-level copy.

## Security-Sensitive Contributions

Read [SECURITY.md](SECURITY.md) before filing or discussing vulnerabilities. Do not put sensitive exploit details, credentials, private media, or private paths in public Issues or pull requests.

## Historical And Generated Material

- `VERSIONS/`, `docs/reports/archive/`, and `src/file_uncorrupter/legacy/` contain historical evidence.
- Generated recovery output, workspace state, databases, caches, and build output should not be committed unless an explicit repository requirement says otherwise.
- Do not edit or delete historical evidence merely to satisfy cleanup patterns.
