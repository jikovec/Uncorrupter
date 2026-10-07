<!-- codex-memory-scaffold:commands -->
# Commands

## Discovered Commands
- python -m pip install -e . - explicit README command, source: README.md; detail: README documented command
- file-uncorrupter - explicit console script, source: pyproject.toml [project.scripts]; detail: dispatches to file_uncorrupter.cli:main
- file-uncorrupter scan - explicit CLI command, source: README.md and src/file_uncorrupter/cli.py; detail: scan and persist file evidence
- file-uncorrupter classify - explicit CLI command, source: README.md and src/file_uncorrupter/cli.py; detail: scan, classify, and persist evidence
- file-uncorrupter recover - explicit CLI command, source: README.md and src/file_uncorrupter/cli.py; detail: recover files into an output directory
- file-uncorrupter benchmark - explicit CLI command, source: README.md and src/file_uncorrupter/cli.py; detail: recover and optionally export JSON/CSV reports
- file-uncorrupter report - explicit CLI command, source: README.md and src/file_uncorrupter/cli.py; detail: export reports from an existing run database
- python -m pytest - explicit README command with pyproject pytest configuration; detail: pytest must be installed in the active Python environment

## Command Sources Inspected
- pyproject.toml
- README.md
- src/file_uncorrupter/cli.py
- docs/api/CLI.md

## Notes
- explicit means the command came from a manifest script, README, Makefile, or CI workflow.
- inferred means the repository shape suggests the command, but it was not directly declared as a script.
- pytest is configured in pyproject.toml, but pytest itself is not declared as a package dependency.
- .env and other secret-bearing files were not read.

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
