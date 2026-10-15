# Quickstart Validation: Stabilized Multi-Format Recovery

## Prerequisites

- Python 3.11 or newer
- Development installation of the project
- Optional FFmpeg/ffprobe for media adapter scenarios
- Optional qpdf, 7-Zip, and LibreOffice/soffice for their adapter scenarios

## Install

~~~powershell
python -m pip install -e ".[dev]"
~~~

## Baseline Quality Gate

~~~powershell
python -m pytest -p no:cacheprovider
python -m build
~~~

Expected:

- all non-optional tests pass
- optional-tool tests either pass or report an explicit skip/unavailable scenario
- the built package reports the same version as the source runtime

## Inspect Capabilities

~~~powershell
file-uncorrupter capabilities
file-uncorrupter capabilities --format json
~~~

Expected:

- every format lists operation levels and tool availability
- no detect-only or adapter-only family is described as full repair

## Safe Recovery

~~~powershell
file-uncorrupter recover .\fixtures\input .\results\safe-run --recursive --all-files --goal repair --goal extract --goal preview --db .\results\runs.sqlite3 --events .\results\events.jsonl --manifest .\results\manifest.json
~~~

Expected:

- inputs remain unchanged
- existing outputs are preserved by default
- artifacts use validated suffixes
- the final manifest records capability, budget, tool, validator, and provenance evidence

## Cancellation And Resume

Create the cancellation marker before a bounded run, remove it, then resume the run identifier with the same effective configuration and goals:

~~~powershell
New-Item -ItemType File -Force .\results\cancel.marker | Out-Null
file-uncorrupter recover .\fixtures\large .\results\resume-run --recursive --all-files --workers 2 --goal repair --db .\results\runs.sqlite3 --cancel-marker .\results\cancel.marker
Remove-Item -LiteralPath .\results\cancel.marker
file-uncorrupter recover .\fixtures\large .\results\resume-run --recursive --all-files --workers 2 --goal repair --db .\results\runs.sqlite3 --resume 1 --changed-input-policy abort
~~~

Expected:

- the first run reaches cancelled without orphan tool processes
- completed matching files are reused
- changed sources are rejected or reprocessed according to the selected policy

## Format Vertical Slices

Run focused tests:

~~~powershell
python -m pytest tests\test_text_handler.py
python -m pytest tests\test_archive_handler.py tests\test_package_documents.py
python -m pytest tests\test_pdf_handler.py
python -m pytest tests\test_image_handlers.py tests\test_media_handlers.py
python -m pytest tests\test_streaming_handlers.py
~~~

Expected:

- text span maps trace output to source bytes
- archives cannot escape output and respect expansion limits
- package documents distinguish validated package from extracted content
- PDF, image, and media claims require independent validation

## Determinism And Benchmark

~~~powershell
file-uncorrupter benchmark .\fixtures\corpus .\results\benchmark-a --recursive --all-files --goal repair --ground-truth .\fixtures\ground-truth.json --manifest .\results\a.json --db .\results\a.sqlite3
file-uncorrupter benchmark .\fixtures\corpus .\results\benchmark-b --recursive --all-files --goal repair --ground-truth .\fixtures\ground-truth.json --manifest .\results\b.json --db .\results\b.sqlite3
~~~

Expected:

- candidate and artifact ordering is stable
- selected artifact hashes match for deterministic fixtures
- reports include recovery, partial, fidelity, runtime, expansion, crash, timeout, budget, and sampled main-process RSS metrics
- labeled ground truth produces global/per-family classification, recovery, fidelity, false-positive, and false-negative metrics; child-process memory remains explicitly excluded
