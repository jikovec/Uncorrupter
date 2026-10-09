# Developer Setup

## Requirements

- Python 3.11, 3.12, or 3.13
- Git for source inspection and diff hygiene
- Pillow (installed as a runtime dependency)
- pytest and build (installed by the `dev` extra)
- Optional tools only for the capabilities being exercised: FFmpeg/ffprobe, qpdf, 7-Zip, LibreOffice, and Pillow codec plugins

Windows PowerShell examples are used because this repository is currently developed on Windows. The defined CI matrix also targets Ubuntu.

## Create An Isolated Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Confirm the version and minimum capability surface:

```powershell
file-uncorrupter --version
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
file-uncorrupter capabilities --format markdown
```

## Run Tests

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
python -m pytest -p no:cacheprovider -q
```

To test installed optional tools separately:

```powershell
Remove-Item Env:\UNCORRUPTER_DISABLE_EXTERNAL_TOOLS -ErrorAction SilentlyContinue
python -m pytest -p no:cacheprovider -q
file-uncorrupter capabilities --format json
```

Always record the resolved tool versions and any skips.

## Build

```powershell
python -m compileall -q src tests
python -m build
```

Build outputs under `dist/` are local artifacts. This command does not publish a package or create a release.

## Safe Development Data Layout

Use disposable, non-overlapping locations:

```text
dev-data/
  input/       # copied/synthetic sources
  output/      # new recovery artifacts
  workspace/   # run configs/reports
  runs.sqlite3 # evidence database
```

Do not use irreplaceable files as fixtures. Do not add real user media/documents, databases, recovery outputs, SQLite evidence, events, or reports to source control.

## Local Smoke Run

```powershell
file-uncorrupter scan .\dev-data\input --recursive --all-files --db .\dev-data\runs.sqlite3
file-uncorrupter classify .\dev-data\input --recursive --all-files --db .\dev-data\runs.sqlite3
file-uncorrupter recover .\dev-data\input .\dev-data\output `
  --recursive --all-files `
  --goal repair --goal extract `
  --db .\dev-data\runs.sqlite3 `
  --workspace-root .\dev-data\workspace `
  --events .\dev-data\events.jsonl `
  --redact-paths
```

## Adding Or Changing A Format

1. Read [current state](../current-state.md), [architecture](../architecture/ARCHITECTURE.md), [source map](../SOURCE-MAP.md), and [capabilities/roadmap](../CAPABILITIES-AND-ROADMAP.md).
2. Add or extend license-safe builders in `tests/fixtures.py` and mutation applicability in `tests/mutations.py`.
3. Add failing handler/safety/fidelity tests.
4. Implement inspect/plan/execute under existing byte-source, budget, cancellation, process, and publication contracts.
5. Register one variant owner.
6. Run focused tests, then the full tool-disabled suite.
7. Update `docs/capabilities.generated.md` from executable output using a reviewable patch.
8. Update narrative docs and `docs/agent-index.json`.
9. Add/update a dated report and handoff.
10. Run compile, build, JSON/YAML, Markdown, capability, and diff-hygiene gates.

Do not advertise a recovery goal before the exact output is published, validated, graded, persisted, and tested.

## Optional Tool Notes

### FFmpeg And ffprobe

When both tools are available, the public media handler enables copy-remux normalization, per-stream extraction, and one-frame preview. Exact temporary outputs must pass ffprobe validation and hash-correlated atomic publication. Tool-absent behavior remains part of the deterministic suite.

### qpdf

Optional PDF repair and validation. Public repair validates the exact qpdf output with qpdf and the native incremental PDF analyzer before atomic publication. Native PDF inspection does not require it.

### 7-Zip

Conditional 7z/RAR listing and extraction adapter. Tool output and extracted members remain bounded and contained.

### LibreOffice

Conditionally enables headless DOC/XLS/PPT conversion to an inert, natively validated PDF preview. The resolver accepts both `libreoffice` and the common Windows `soffice` command. This is preview-only and not editable Office recovery.

### Isolation Wrapper

The application does not install a sandbox. Supply a trusted local wrapper with `--require-tool-isolation --isolation-wrapper ...`; missing wrappers fail closed.

## Generated And Local-Only Paths

- `.venv/`, `build/`, `dist/`, caches, bytecode: generated development artifacts.
- `.uncorrupter-workspace/`, output directories, databases, JSONL, reports: local recovery evidence.
- `.obsidian/`: ignored local editor settings.
- `.agents/`, `.specify/`: local-only workflow scaffolding.
- `VERSIONS/`: historical project artifacts, not the current implementation source.

## Documentation Checks

```powershell
python -m json.tool .\docs\agent-index.json > $null
python -m pytest -p no:cacheprovider -q tests\test_capabilities.py tests\test_mutation_inventory.py tests\test_packaging.py
python -m pytest -p no:cacheprovider -q tests\test_streaming_handlers.py tests\test_benchmarking.py
git diff --check
```

See [Testing and verification](../testing/VERIFICATION.md) for the complete evidence boundary.
