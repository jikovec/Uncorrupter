<!-- codex-memory-scaffold:commands -->
# Commands

## Install And Inspect

```powershell
python -m pip install -e ".[dev]"
file-uncorrupter --version
file-uncorrupter --help
file-uncorrupter capabilities
file-uncorrupter capabilities --format json
file-uncorrupter capabilities --format markdown --output .\capabilities.md
```

## Product Commands

```powershell
file-uncorrupter scan .\input --recursive --all-files --db .\runs.sqlite3
file-uncorrupter classify .\input --recursive --all-files --db .\runs.sqlite3
file-uncorrupter recover .\input .\output --recursive --all-files --goal repair --goal extract --db .\runs.sqlite3
file-uncorrupter benchmark .\input .\output --recursive --all-files --goal repair --ground-truth .\corpus-ground-truth.json --db .\runs.sqlite3
file-uncorrupter report --db .\runs.sqlite3 --run-id 1 --output-json .\report.json --output-csv .\attempts.csv --output-text .\report.txt
```

See [CLI reference](api/CLI.md) before using resume, cancellation, risky layout, replacement-sensitive paths, external tools, or custom budgets.

## Deterministic Local Verification

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -p no:cacheprovider -q
python -m compileall -q src tests
python -m build
python -m json.tool .\docs\agent-index.json > $null
git diff --check
```

Focused governance gate:

```powershell
python -m pytest -p no:cacheprovider -q tests\test_capabilities.py tests\test_mutation_inventory.py tests\test_packaging.py
python -m pytest -p no:cacheprovider -q tests\test_streaming_handlers.py tests\test_benchmarking.py
```

Optional-tool validation is a separate run:

```powershell
Remove-Item Env:\UNCORRUPTER_DISABLE_EXTERNAL_TOOLS -ErrorAction SilentlyContinue
python -m pytest -p no:cacheprovider -q
file-uncorrupter capabilities --format json
```

Record exact tool identity, result, and skips. Do not merge tool-disabled and tool-present evidence into one claim.

## Capability Baseline Maintenance

The checked baseline is generated with optional tools disabled and compared exactly in tests.

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
file-uncorrupter capabilities --format markdown
python -m pytest -p no:cacheprovider -q tests\test_capabilities.py
```

Review and patch `docs/capabilities.generated.md` only when handler truth intentionally changes.

## Agent toolkit checks

Run from the repository root with the declared Python runtime:

```sh
python .agent/hooks/validate-toolkit/validate.py
python .agent/hooks/validate-toolkit/test_validate.py
python -m json.tool docs/agent-index.json
git diff --check
```

[Canonical skills](../.agent/README.md) are agent workflows, not shell commands.
Use `push` for source delivery and `deploy` for a configured live target; the old
local deploy-as-push command is superseded by the toolkit adoption.

## Command Sources

| Command | Authority |
| --- | --- |
| `file-uncorrupter` | `pyproject.toml` console script and `src/file_uncorrupter/cli.py` |
| `python -m pytest` | `pyproject.toml` dev dependency and pytest config |
| `python -m build` | `pyproject.toml` build system and dev dependency |
| capability/doc gates | `tests/test_capabilities.py`, `tests/test_packaging.py` |
| agent toolkit checks | `.agent/hooks/validate-toolkit/` |

## Safety Notes

- Commands in this file are examples, not authorization to mutate Git/remotes or process arbitrary third-party data.
- Use disposable inputs/outputs for tests.
- Do not expose secrets through command arguments, logs, reports, or fixtures.
- Build success is not package publication; workflow definition is not remote execution; push is not deployment.
