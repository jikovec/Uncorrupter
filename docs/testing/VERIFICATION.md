# Testing And Verification

This document distinguishes what can be reproduced locally from what remains unverified. A passing test proves only the named code path and fixtures in that environment.

## Clean Development Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`Pillow` is the runtime dependency. `pytest` and `build` are declared in the `dev` extra. Optional external tools are not Python dependencies.

## Deterministic Core Suite

Run the complete suite without external tools:

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -p no:cacheprovider -q
```

This is the baseline used for capability-document determinism and should not depend on local FFmpeg/qpdf/7-Zip/LibreOffice installations.

## Optional-Tool Suite

With intended tools explicitly installed and on `PATH`:

```powershell
Remove-Item Env:\UNCORRUPTER_DISABLE_EXTERNAL_TOOLS -ErrorAction SilentlyContinue
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -p no:cacheprovider -q
file-uncorrupter capabilities --format json
```

Record exact resolved paths/versions and skipped tests. A tool-present green run is separate evidence from the deterministic tool-disabled run.

Reviewed 2026-08-08 local evidence:

- tool-disabled full suite: `154 passed, 1 skipped, 1 warning`;
- tool-present full suite: `155 passed, 1 warning`;
- focused media/recovery/integration suite: `21 passed` with FFmpeg and ffprobe `8.1.2`;
- qpdf, 7-Zip, LibreOffice, and `soffice` were unavailable on the reviewed machine, so their tool-present behavior remains controlled-test rather than real-tool evidence.

## Focused Gates

```powershell
python -m pytest -p no:cacheprovider -q tests\test_budgets_and_byte_source.py tests\test_atomic_and_paths.py tests\test_process_runner.py
python -m pytest -p no:cacheprovider -q tests\test_run_lifecycle.py tests\test_cli.py tests\test_benchmarking.py
python -m pytest -p no:cacheprovider -q tests\test_capabilities.py tests\test_mutation_inventory.py tests\test_packaging.py
python -m pytest -p no:cacheprovider -q tests\test_text_handler.py tests\test_archive_handler.py tests\test_package_documents.py tests\test_pdf_handler.py tests\test_streaming_handlers.py
python -m pytest -p no:cacheprovider -q tests\test_image_handlers.py tests\test_media_handlers.py tests\test_external_adapters.py tests\test_multiformat_integration.py
```

## What The Suite Covers

### Core Safety

- sparse/large-file streaming without whole-source loading;
- source identity changes;
- budget fail-before-consume behavior;
- path layout and containment;
- traversal/drive/UNC/reserved-name rejection;
- output collision policy and temporary-file cleanup;
- source/output hash preservation;
- symlink/reparse rejection;
- process timeout, bounded output, minimal environment, cancellation/tree cleanup, tool identity, and required isolation.

### Lifecycle And Evidence

- schema version and additive migrations;
- run/file lifecycle transitions;
- per-file rollback boundaries;
- resume identity/config compatibility;
- unchanged skip and changed abort/reprocess behavior;
- cancellation marker;
- deterministic manifest ordering and path redaction;
- two-independent-run normalized manifest/artifact/strategy/hash determinism;
- all eight outcome grades across JSON, JSONL, CSV, and text reports;
- typed source/artifact/text/archive/document/media/tool relations.

### CLI And Packaging

- parser and command distinction;
- capability formats and quality gate;
- explicit goals and unsupported behavior;
- layout rejection before database creation;
- exit policies and no-result/fatal codes;
- report/event outputs;
- one package/runtime version source;
- declared dev dependencies;
- defined CI matrix and package build.

### Format Families

- encoding matrix, invalid/binary spans, structured diagnostics, and normalization;
- ZIP/TAR checksum, reconstruction/resynchronization, traversal, duplicate, encryption, and expansion fixtures;
- Open XML/OpenDocument required parts, relationships, macro/active content, extraction/rebuild;
- PDF structure/repair/extraction and qpdf absent/present boundary;
- JPEG/PNG/GIF/BMP/WebP/TIFF structural/fidelity behavior and optional codecs;
- video/audio container headers, indexes, continuity, tool absence, copy-remux, stream extraction, preview, exact output validation, and persisted coverage/tool evidence;
- 7z/RAR/RTF/OLE adapter safety and bounded LibreOffice PDF preview simulation;
- end-to-end representative routing/persistence.

### Streaming And Memory Regressions

- public ZIP, DOCX, PDF, TIFF preview, and AVI repair paths run with inputs larger than a 32-byte materialization limit and consume zero materialized source bytes;
- a 16 MiB stored ZIP validates/extracts through the streaming path with less than 12 MiB traced Python allocation peak;
- the benchmark RSS sampler records platform method, samples, baseline, peak, and delta while explicitly excluding child-process memory.

### Mutation Governance

`tests/fixtures.py`, `tests/mutations.py`, and `tests/test_mutation_inventory.py` provide license-safe synthetic evidence for every public capability family. Core cases are:

- valid;
- head and tail truncation;
- prefix and suffix garbage;
- bit flip;
- wrong suffix;
- empty input.

Format-applicable cases include missing indexes, oversized declarations, path attacks, and resource/expansion attacks. The inventory test fails when a public family has no fixture owner or a required class disappears.

## Capability Documentation Gate

The checked baseline uses external tools disabled:

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
file-uncorrupter capabilities --format markdown
python -m pytest -p no:cacheprovider -q tests\test_capabilities.py
```

`test_generated_capability_document_has_no_drift` compares the executable Markdown output byte-for-byte with `docs/capabilities.generated.md`.

## Compile And Package Gates

```powershell
python -m compileall -q src
python -m build
```

The build should create sdist/wheel artifacts under ignored `dist/`. Building locally is not publishing.

## Documentation And Configuration Gates

```powershell
python -m json.tool .\docs\agent-index.json > $null
python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text(encoding='utf-8')); print('ci yaml ok')"
git diff --check
```

The stabilization verification also checks local Markdown links and balanced fenced code blocks. Link validation must ignore URL targets, anchors, generated/local ignored trees, and documented intentionally historical paths only when explicitly allowlisted.

## Manual CLI Smoke Test

Use disposable directories outside important data:

```powershell
New-Item -ItemType Directory -Force .\smoke-input, .\smoke-output | Out-Null
Set-Content -LiteralPath .\smoke-input\sample.md -Value "# Sample`n```text`ntruncated" -NoNewline
file-uncorrupter capabilities
file-uncorrupter scan .\smoke-input --all-files --db .\smoke.sqlite3
file-uncorrupter classify .\smoke-input --all-files --db .\smoke.sqlite3
file-uncorrupter recover .\smoke-input .\smoke-output --all-files --goal repair --goal preview --db .\smoke.sqlite3 --events .\smoke-events.jsonl
file-uncorrupter report --db .\smoke.sqlite3 --output-json .\smoke-report.json --output-text .\smoke-report.txt
```

Review source hash, artifact namespace, fidelity grades, JSONL sequence, and report content. Clean up only disposable paths you created and verified.

## Benchmark Interpretation

The benchmark manifest records recovery/partial rates, fidelity grades, runtime, input/output/expansion, crashes, timeouts, budget stops, cancellations, and sampled main-process RSS. With the version 1 [ground-truth contract](../BENCHMARK-GROUND-TRUTH.md), it also computes global/per-family classification, recovery, and fidelity accuracy plus false-positive and false-negative rates. Without required labels, those label-dependent rates remain unavailable.

A release-quality benchmark still needs:

- a license-safe, labeled real-world corpus;
- expected recovered content/hash assertions;
- exact tool and platform identities;
- repeatability comparison;
- whole process-tree peak-memory measurement for child tools;
- enough positive/negative labels for statistically useful per-format estimates;
- documented thresholds for each support tier.

## CI Boundary

`.github/workflows/ci.yml` defines:

- Ubuntu and Windows;
- Python 3.11, 3.12, and 3.13;
- external-tool-disabled full tests;
- capability/documentation consistency;
- package build;
- an Ubuntu FFmpeg-present job.

The workflow definition is inspected and locally parsed. It is not a claim that GitHub Actions ran on the current exact commit. Remote execution, check conclusions, branch protection, and release status require separate evidence.

## Evidence Labels

- **Inspected**: source/config/docs were read.
- **Implemented**: files were changed.
- **Tested**: a named local check actually ran.
- **Simulated**: synthetic fixtures or substitute tools were used.
- **Live-verified**: the intended live target was directly checked.
- **Deployed**: an authorized deployment was performed and confirmed.
- **Unverified**: no adequate check supports the claim.

Current format evidence is predominantly tested with deterministic synthetic fixtures. It is not live deployment or broad corpus proof.
