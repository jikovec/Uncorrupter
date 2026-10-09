# Project Overview

File Uncorrupter is an offline-first, evidence-preserving recovery framework for untrusted files. It is implemented as a Python 3.11+ CLI and local library. Its job is to recover defensible bytes and structure into new artifacts while retaining enough evidence to explain what was detected, attempted, selected, published, skipped, or stopped.

## Current Project Card — 2026-09-09

This review describes the existing local candidate, not only committed remote source. The catalogue checkout is accessible; its machine-specific location stays in the external catalogue. Use `git rev-parse --show-toplevel` and `realpath .` to resolve the current checkout without embedding host paths in portable documentation.

| Field | Current evidence |
| --- | --- |
| Identity and purpose | File Uncorrupter / UNCorrupter: offline bounded damaged-file recovery, immutable source evidence, disposable output, provenance, hostile input/resource limits, honest recovery capabilities. |
| Owner and canonical remote | Repository owner `jikovec`; public `https://github.com/jikovec/Uncorrupter`, default branch `main`, confirmed by a read-only GitHub connector request. Package author metadata still says `OpenAI`; authorship intent remains an owner decision. |
| Source identity | Local HEAD and live remote `main`: `70fd1188d3a0ff9ea08e526924eada70532cb582`. The extensive dirty/untracked local `0.4.0` candidate is not represented by that commit. |
| Canonical local material | `src/file_uncorrupter/`, `pyproject.toml`, `tests/`; navigation starts at `00_Index.md`. Historical archives and dated reports remain evidence, not runtime authority. |
| Data locations | Inputs and output roots are caller-selected. DB defaults to `runs.sqlite3`. Default workspace is `<output-root>/.uncorrupter-workspace/` when output exists, otherwise beside the DB; explicit `--workspace-root` overrides it. Workspace subdirectories are `blobs/`, `outputs/`, `reports/`, `configs/`. No authoritative private input collection was designated or inspected. |
| Implemented scope | Ten operation-specific handler families listed below; six commands: capabilities, scan, classify, recover, benchmark, report. Explicit goals: repair (default), normalize, extract, preview, carve. |
| Lifecycle | Validate layout/config → deterministic discovery and identity checks → read-only inspection/classification → requested goal planning/execution → atomic artifacts and per-file SQLite evidence → final reports. Resume creates linked new runs; changed sources use abort, skip, or reprocess. |
| Dependencies | Python >=3.11; declared CI versions 3.11–3.13; Pillow >=10; setuptools >=69 and wheel; dev extra build >=1.2 and pytest >=8,<10. SQLite is standard library. FFmpeg/ffprobe, qpdf, 7-Zip, LibreOffice and image codecs are optional. No project runtime lock or Nix environment definition was found. |
| Current host readiness | Neither python/python3 nor file-uncorrupter, pytest, uv, FFmpeg/ffprobe, qpdf or 7z resolves on PATH. LibreOffice resolves, but its adapter/version was not executed. Existing Python-based environment actions need a project development runtime. Historical Windows test results remain historical. |
| Existing agent setup | Reuse `docs/agent-workflow.md`, `uncorrupter-workflow`, local Spec Kit skills and the separately invoked `deploy` skill. `.codex/environments/environment.toml` has four manual Linux actions and empty setup/cleanup scripts. No new command system is needed. |
| Connectors and tools | GitHub repository metadata read succeeded in this session. Local Git/shell are usable. Atlassian and Cloudflare connector tools are exposed but were not connection-tested and have no established project role. PDF/document skills are available for separately scoped artifact inspection. No connector is part of the recovery runtime. |
| Publication triggers | Local, untracked `.github/workflows/ci.yml` defines push and pull_request CI with tests/build and an FFmpeg job; no release/upload/Pages/deployment job. Git hooks contain samples only; no core.hooksPath override. Remote automation outside this checkout was not audited. |
| Evidence boundary | Documentation/source inspection now; earlier synthetic Windows test evidence remains in its dated report. No current-host Python tests, build, runtime capabilities, exact-candidate remote CI, release, deployed identity, or live acceptance was established. |

Exact setup and execution examples remain in [Developer setup](setup/DEVELOPMENT.md), [Commands](commands.md), and [CLI reference](api/CLI.md). These are supported command contracts, not a claim they executed on this host:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
file-uncorrupter --version
file-uncorrupter capabilities --format json
file-uncorrupter scan ./input --recursive --all-files --db ./runs.sqlite3
file-uncorrupter classify ./input --recursive --all-files --db ./runs.sqlite3
file-uncorrupter recover ./input ./output --recursive --all-files --goal repair --goal extract --db ./runs.sqlite3
file-uncorrupter benchmark ./input ./output --recursive --all-files --goal repair --ground-truth ./corpus-ground-truth.json --db ./runs.sqlite3
file-uncorrupter report --db ./runs.sqlite3 --run-id 1 --output-json ./report.json --output-csv ./attempts.csv --output-text ./report.txt
UNCORRUPTER_DISABLE_EXTERNAL_TOOLS=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q
UNCORRUPTER_DISABLE_EXTERNAL_TOOLS=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q tests/test_capabilities.py tests/test_mutation_inventory.py tests/test_packaging.py
python -m build
python -m json.tool ./docs/agent-index.json
git diff --check
```

The shell activation line is the POSIX equivalent of the existing PowerShell venv setup. Establish an available supported Python first; this review installed nothing and did not create a venv. Recovery examples require caller-owned or synthetic input and fresh, non-overlapping output/evidence destinations.

The September 5 attachment describes older committed code: its missing workflow, version mismatch, undeclared pytest, media-only scope, and absent source/layout/budget guards do not describe this local candidate. Disposable output means reproducible derived artifacts, not automatic disposal or authorization to delete evidence. Resource guards do not provide an OS sandbox or a hard whole-process-tree memory cap; optional path pseudonymization does not make reports safe to publish automatically.

Remaining decisions: establish the supported project Python environment on this host; confirm package authorship metadata; decide any later candidate publication/CI/protection/release scope separately. Remaining engineering evidence includes real optional-tool matrices, whole-process-tree limits, independent security review/fuzzing, and a licensed labeled real-world corpus. Remote dev-branch ancestry from the attachment was not rechecked and creates no cleanup instruction. See the [dated orientation handoff](../handoffs/2026-09-09-local-orientation.md).

## Product Principles

- Source files are immutable evidence.
- Recovery goals are explicit and never silently substituted.
- Partial content and previews are useful but must not be called complete recovery.
- Every expensive or expansive operation is bounded.
- Existing outputs are preserved by default.
- Optional tools are capabilities, not hidden assumptions.
- Active content is inert; encryption is reported, not bypassed.
- A green test is evidence for its fixtures only, not a production or deployment claim.

## Current Package Shape

| Layer | Responsibility |
| --- | --- |
| CLI | Parse commands, validate layout/configuration, manage lifecycle/resume, choose exit policy, and separate stdout/stderr/events. |
| Intake and byte source | Deterministic discovery, symlink/reparse rejection, streaming identity/hash evidence, bounded slices, and a read-only seekable parser adapter. |
| Detection/classification | Keep extension, byte-0 signature, anywhere signature, and structure evidence distinct. |
| Handler registry | Own public format variants and expose capability/inspect/plan/execute contracts. |
| Recovery coordinator | Run bounded workers, goals, plans, cancellation checkpoints, source rechecks, and persistence. |
| Publication | Contained, no-clobber, temporary-sibling atomic artifact writes. |
| Evidence store | SQLite schema version 2, typed relations, events, budgets, tools, and lifecycle state. |
| Reporting and benchmarking | Deterministic manifest ordering, JSONL/JSON/CSV/text outcome evidence, labeled ground-truth evaluation, main-process RSS sampling, and optional path redaction. |

## Public Commands

- `capabilities`
- `scan`
- `classify`
- `recover`
- `benchmark`
- `report`

See [CLI reference](api/CLI.md) for exact behavior and options.

## Public Format Families

The registry currently contains ten capability families:

1. `text`
2. `archive`
3. `package_document`
4. `pdf`
5. `jpeg`
6. `image`
7. `media`
8. `external_archive`
9. `rtf`
10. `legacy_office`

These cover, at different depths:

- `.txt`, `.md`, `.markdown`, `.log`, `.csv`, `.json`, `.xml`, `.html`, `.htm`
- `.zip`, `.tar`, `.7z`, `.rar`
- `.docx`, `.docm`, `.xlsx`, `.xlsm`, `.pptx`, `.pptm`, `.odt`, `.ods`, `.odp`
- `.pdf`, `.rtf`, `.doc`, `.xls`, `.ppt`
- `.jpg`, `.jpeg`, `.jpe`, `.png`, `.gif`, `.bmp`, `.webp`, `.tif`, `.tiff`, `.heif`, `.heic`, `.avif`, `.jp2`, `.j2k`, `.jpx`, common RAW suffixes
- `.mp4`, `.m4v`, `.mov`, `.mkv`, `.webm`, `.avi`, `.ts`, `.mts`, `.m2ts`, `.mpg`, `.mpeg`, `.flv`, `.asf`, `.wmv`
- `.wav`, `.mp3`, `.flac`, `.aac`, `.ogg`, `.oga`

An extension in the registry does not mean every operation is available. The [generated capability baseline](capabilities.generated.md) and the live `capabilities` command define the exact boundary.

## Recovery Outcomes

The framework separates artifact purpose from fidelity:

- artifact kinds: repaired, normalized, extracted, preview, frame, raw fragment, diagnostics, manifest;
- fidelity/outcome grades: validated original, validated normalized, partial content, preview only, unavailable dependency, budget exceeded, cancelled, failed.

This lets a damaged DOCX yield valid text and media artifacts without pretending the original package was fully recovered. A video may yield native structure only, a validated copy-remux when FFmpeg/ffprobe are present, or one preview frame; each result remains a different claim.

## Safety Envelope

The default model is local and fail-closed:

- no source-path writes;
- no output overwrite;
- no archive traversal or link/device extraction;
- no password cracking;
- no macro/script/HTML/embedded-object execution;
- bounded source reads, materialization, candidates, tools, decompression, recursion, artifacts, output, and workers;
- optional external tools execute through one recorded, cancellable policy;
- optional required isolation wrapper prevents launch when unavailable;
- source identity is checked before/after work;
- interrupted runs preserve completed file evidence.

## Technology

- Python 3.11+
- setuptools build backend
- Pillow runtime dependency
- SQLite standard-library persistence
- pytest/build in the `dev` extra
- optional FFmpeg/ffprobe, qpdf, 7-Zip, LibreOffice, and Pillow format plugins
- GitHub Actions matrix defined for Windows/Linux and Python 3.11-3.13

## Important Paths

| Path | Role |
| --- | --- |
| `src/file_uncorrupter/cli.py` | Public command parser and run orchestration. |
| `src/file_uncorrupter/pipeline.py` | Analysis/recovery coordination and persistence bridge. |
| `src/file_uncorrupter/handlers/` | Public format contracts and handlers. |
| `src/file_uncorrupter/byte_source.py` | Immutable bounded source access. |
| `src/file_uncorrupter/budgets.py` | Resource contracts and counters. |
| `src/file_uncorrupter/atomic.py` | Safe artifact publication. |
| `src/file_uncorrupter/process_runner.py` | Unified optional-tool boundary. |
| `src/file_uncorrupter/db.py` | Schema/migrations/evidence queries. |
| `src/file_uncorrupter/reporting.py` | Manifest and report generation. |
| `src/file_uncorrupter/benchmarking.py` | Ground-truth validation/evaluation and main-process RSS sampling. |
| `tests/` | Synthetic fixtures, mutations, safety, lifecycle, handlers, CLI, capability, and packaging gates. |
| `docs/capabilities.generated.md` | Checked executable tool-disabled support baseline. |
| `reports/` | Dated implementation/audit evidence. |
| `handoffs/` | Durable future-agent state. |
| `VERSIONS/` | Historical artifacts, not current source authority. |

## Non-Goals At The Current Boundary

- Inventing missing user content.
- Modifying a damaged source in place.
- Password recovery, encryption bypass, or DRM/key circumvention.
- Executing embedded code or opening recovered files in their native applications.
- Claiming all registered extensions have full repair support.
- Claiming a format is safe because a parser accepted it.
- Cloud upload, accounts, telemetry, or automatic publication.
- Production deployment or release orchestration.

## Where To Go Next

- [Current state](current-state.md)
- [Capabilities and roadmap](CAPABILITIES-AND-ROADMAP.md)
- [Benchmark ground truth](BENCHMARK-GROUND-TRUTH.md)
- [Architecture](architecture/ARCHITECTURE.md)
- [Source map](SOURCE-MAP.md)
- [Connection map](CONNECTIONS.md)
- [Security](security/SECURITY.md)
- [Testing](testing/VERIFICATION.md)
- [Implementation report](../reports/2026-08-05-stabilized-multiformat-implementation.md)
