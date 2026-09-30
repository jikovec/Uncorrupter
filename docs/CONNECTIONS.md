# Connection Map

Tags: #repo/connection-map #agent/orientation #uncorrupter/evidence

## Documentation To Source

- [Architecture](architecture/ARCHITECTURE.md) -> CLI, pipeline, engines, decoders, persistence, workspace.
- [CLI reference](api/CLI.md) -> `src/file_uncorrupter/cli.py` and `pyproject.toml`.
- [Security model](security/SECURITY.md) -> local file handling, decoder subprocesses, persistence/privacy boundaries.
- [Testing](testing/VERIFICATION.md) -> `pyproject.toml` and the current `tests/test_*.py` suite.
- [Source map](SOURCE-MAP.md) -> every current package and test responsibility.

## Repository Policy To Canonical Docs

- [../SECURITY.md](../SECURITY.md) is the GitHub-discovery security entry point and routes to [security/SECURITY.md](security/SECURITY.md).
- [../CONTRIBUTING.md](../CONTRIBUTING.md) defines the contribution/delivery workflow and routes to [setup/DEVELOPMENT.md](setup/DEVELOPMENT.md) and [testing/VERIFICATION.md](testing/VERIFICATION.md).
- [../SUPPORT.md](../SUPPORT.md) defines the supported public support routes without promising an SLA.

## Source To Tests

- `classification.py` -> `tests/test_classification.py`
- `signature_index.py` -> `tests/test_signature_index.py`
- `db.py` -> `tests/test_db.py`
- engines/decoders/recovery pipeline -> `tests/test_recovery.py`

CLI parsing is currently covered indirectly rather than by a dedicated CLI test module.

## Reports And Handoffs

- [../reports/](../reports/) stores durable validation, implementation, and audit evidence.
- [reports/](reports/) stores curated documentation reports and historical research.
- [../handoffs/](../handoffs/) stores specific deferred-work notes for a future agent.

When a report materially changes the current understanding of the repository, update the relevant current-state/map/index documents rather than treating the report itself as canonical implementation truth.

## Work Ledger And Delivery

Material current/future work is tracked in GitHub Issues. Repository changes should normally flow through:

`Issue -> branch -> implementation -> verification -> pull request`

No current deployment workflow exists. A merge must not be described as deployment, publication, or release.

## Machine-Readable Index

[agent-index.json](agent-index.json) mirrors the agent-facing paths, commands, safety boundaries, and known risks. Keep it repository-relative and free of secrets or private local information.
