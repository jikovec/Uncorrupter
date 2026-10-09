<!-- codex-memory-scaffold:testing -->
# Testing

The canonical verification guide is [testing/VERIFICATION.md](testing/VERIFICATION.md).

## Primary Commands

Deterministic tool-disabled suite:

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -p no:cacheprovider -q
```

Compile and package:

```powershell
python -m compileall -q src tests
python -m build
```

Capability/documentation gate:

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
python -m pytest -p no:cacheprovider -q tests\test_capabilities.py tests\test_mutation_inventory.py tests\test_packaging.py
python -m pytest -p no:cacheprovider -q tests\test_streaming_handlers.py tests\test_benchmarking.py
```

Metadata/docs hygiene:

```powershell
python -m json.tool .\docs\agent-index.json > $null
git diff --check
```

## Verification Notes

- Install development dependencies with `python -m pip install -e ".[dev]"`.
- Run a separate optional-tool-present suite when validating FFmpeg, qpdf, 7-Zip, LibreOffice, or Pillow codec behavior.
- Skips must be reported with their reason; they are not passes for the skipped capability.
- Synthetic fixtures prove their paths only. They do not establish real-world recovery rates, security certification, CI execution, deployment, or release readiness.
- Exact current evidence belongs in the dated implementation report, not in an undated green-test claim.
