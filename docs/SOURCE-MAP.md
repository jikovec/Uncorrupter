# Source Map

This map orients maintainers from public behavior to its owning code and evidence. Current source, `pyproject.toml`, and executable tests override historical reports.

## Public And Package Surfaces

| Path | Role | Primary checks |
| --- | --- | --- |
| `pyproject.toml` | Build metadata, Python floor, runtime/dev dependencies, console script, pytest config. | `tests/test_packaging.py` |
| `src/file_uncorrupter/__init__.py` | Authoritative `__version__`. | `tests/test_packaging.py`, CLI version tests |
| `src/file_uncorrupter/cli.py` | Parser, commands, lifecycle, resume, reports, exit policy. | `tests/test_cli.py`, `tests/test_run_lifecycle.py` |
| `src/file_uncorrupter/capabilities.py` | Handler-derived JSON/text/Markdown manifests and quality gate. | `tests/test_capabilities.py` |

## Stabilization Core

| Path | Role | Primary checks |
| --- | --- | --- |
| `budgets.py` | Resource defaults, hierarchical fail-before-consume counters/events. | `test_budgets_and_byte_source.py`, `test_safe_recovery.py` |
| `byte_source.py` | Immutable identity, streaming/random reads, read-only seekable parser adapter, slices, hash, change detection. | `test_budgets_and_byte_source.py`, `test_run_lifecycle.py`, `test_streaming_handlers.py` |
| `paths.py` | Layout overlap and contained relative-path validation. | `test_atomic_and_paths.py`, `test_cli.py` |
| `atomic.py` | Temporary-sibling durable publication and collision policy. | `test_atomic_and_paths.py`, `test_safe_recovery.py` |
| `cancellation.py` | Cancellation token and marker-file integration. | `test_process_runner.py`, `test_run_lifecycle.py` |
| `events.py` | Durable deterministic JSONL and path pseudonymization. | `test_cli.py`, `test_run_lifecycle.py` |
| `process_runner.py` | Minimal-env bounded subprocess/tool/isolation boundary. | `test_process_runner.py`, `test_external_adapters.py`, `test_pdf_handler.py` |
| `types.py` | File, signature, classification, plan, candidate, decode, artifact, outcome types. | Cross-suite |

## Intake, Detection, And Routing

| Path | Role | Primary checks |
| --- | --- | --- |
| `constants.py` | Extensions, families, signatures, format mappings. | `test_classification.py`, `test_capabilities.py` |
| `intake.py` | Stable discovery, reparse pruning, source record construction. | `test_safe_recovery.py`, `test_cli.py` |
| `signature_index.py` | Bounded byte-0/anywhere signature hits. | `test_signature_index.py`, `test_classification.py` |
| `classification.py` | Evidence separation and family/label/confidence. | `test_classification.py`, `test_capabilities.py` |
| `handlers/base.py` | Handler/capability/context/goal/plan contract. | `test_handler_registry.py` |
| `handlers/registry.py` | Deterministic ownership and handler lookup. | `test_handler_registry.py`, `test_capabilities.py` |
| `pipeline.py` | Analyze/process coordinators, budgets, goals, workers, persistence bridge. | `test_safe_recovery.py`, `test_run_lifecycle.py`, `test_multiformat_integration.py` |

## Format Handlers

| Path | Formats | Primary checks |
| --- | --- | --- |
| `handlers/text.py` | TXT, Markdown, log, CSV, JSON, XML, HTML. | `test_text_handler.py` |
| `handlers/archive.py` | Streaming ZIP/TAR validation/extraction and bounded reconstruction. | `test_archive_handler.py`, `test_streaming_handlers.py` |
| `handlers/package_document.py` | Streaming DOCX/DOCM, XLSX/XLSM, PPTX/PPTM, ODT/ODS/ODP inspection/extraction and bounded rebuild. | `test_package_documents.py`, `test_streaming_handlers.py` |
| `handlers/pdf.py` | Incremental PDF analysis/extraction, bounded native repair, exact-output qpdf repair/validation. | `test_pdf_handler.py`, `test_streaming_handlers.py` |
| `handlers/image.py` | PNG, GIF, BMP, WebP, seekable TIFF, HEIF/AVIF/JP2/RAW boundaries. | `test_image_handlers.py`, `test_streaming_handlers.py` |
| `handlers/legacy_media.py` | JPEG public handler bridge. | `test_recovery.py`, `test_image_handlers.py`, `test_multiformat_integration.py` |
| `handlers/media.py` | Streaming video/audio diagnostics/native repair plus conditional FFmpeg normalize/extract/preview. | `test_media_handlers.py`, `test_multiformat_integration.py`, `test_streaming_handlers.py` |
| `handlers/external.py` | 7z/RAR, RTF, and conditional LibreOffice/soffice legacy DOC/XLS/PPT preview. | `test_external_adapters.py` |

## Candidate Engines And Decoders

| Path | Role | Boundary |
| --- | --- | --- |
| `engines/base.py` | Compatibility engine interface. | Not the public handler contract. |
| `engines/jpeg_v1.py` | JPEG structural candidate strategies. | Bounded/capped by the JPEG handler. |
| `engines/media_v2.py` | Baseline candidate generation and content/strategy deduplication. | Compatibility and reusable candidate logic. |
| `engines/registry.py` | Legacy engine selection. | Kept for compatibility. |
| `decoders.py` | Seekable Pillow/file-output validation plus FFmpeg/ffprobe normalize/extract/preview primitives. | Public operations require handler plans and exact published-output validation. |
| `scoring.py` | Candidate scoring. | Selection evidence, not proof of full fidelity. |

## Persistence, Workspace, And Reporting

| Path | Role | Primary checks |
| --- | --- | --- |
| `db.py` | Schema v2, migrations, lifecycle, typed relations, summaries/resume queries. | `test_db.py`, `test_db_migrations.py`, `test_run_lifecycle.py` |
| `workspace.py` | Local workspace layout and atomic config/blob helpers. | `test_atomic_and_paths.py`, CLI integration |
| `reporting.py` | JSON manifest, CSV, text, benchmark, redaction. | `test_cli.py`, `test_run_lifecycle.py` |
| `benchmarking.py` | Ground-truth validation/evaluation and main-process RSS sampling. | `test_benchmarking.py`, `test_cli.py` |

## Fixture And Quality Infrastructure

| Path | Role |
| --- | --- |
| `tests/fixtures.py` | License-safe deterministic builders and public-family evidence inventory. |
| `tests/mutations.py` | Core and format-specific mutation case construction. |
| `tests/test_mutation_inventory.py` | Ensures every public family and required mutation class stays represented. |
| `tests/test_capabilities.py` | Manifest completeness, unique ownership, fixture evidence, generated-doc drift. |
| `tests/test_packaging.py` | Version/dependency/workflow/build surface checks. |
| `tests/test_streaming_handlers.py` | Zero-materialization public-handler paths and large stored-ZIP memory regression. |
| `tests/test_determinism.py` | Stable fixture/candidate behavior independent of hash seed and run. |
| `.github/workflows/ci.yml` | Defined Windows/Linux/Python/tool matrix; not itself proof of remote execution. |

## Documentation And Evidence

| Path | Role |
| --- | --- |
| `README.md` | User entry point and safe workflow. |
| `docs/current-state.md` | Confirmed implementation and open gates. |
| `docs/capabilities.generated.md` | Executable tool-disabled capability baseline. |
| `docs/CAPABILITIES-AND-ROADMAP.md` | Format detail and future possibilities. |
| `docs/BENCHMARK-GROUND-TRUTH.md` | Versioned benchmark label schema and metric semantics. |
| `docs/architecture/ARCHITECTURE.md` | Component contracts and data flow. |
| `docs/security/SECURITY.md` | Threat model and non-guarantees. |
| `docs/testing/VERIFICATION.md` | Reproduction and evidence labels. |
| `reports/2026-08-05-stabilized-multiformat-implementation.md` | Dated implementation/test evidence. |
| `handoffs/2026-08-05-stabilized-multiformat-recovery.md` | Future-agent continuation boundary. |

## Historical Boundaries

- `VERSIONS/`, `CHANGELOG/`, `DOCUMENTATION/`, `results/`, and archived reports may explain earlier prototypes but do not override current source.
- `.uncorrupter-workspace/`, `output/`, and `single-input/` are local run/input artifacts, not product source.
- `.agents/` and `.specify/` are local workflow scaffolding.
- `.obsidian/` is local ignored editor state.

## Change Checklist

When a path, command, capability, safety rule, or known risk changes, update:

1. the owning executable tests;
2. `docs/capabilities.generated.md` if capability output changes;
3. the relevant source/architecture/current-state docs;
4. `docs/agent-index.json`;
5. a dated report or handoff for substantive changes.

## Development agent infrastructure

[AGENTS.md](../AGENTS.md) routes to [.agent/](../.agent/README.md) shared contracts,
[skills/](../skills/) reasoning workflows and thin native provider adapters.
[Toolkit validation](../.agent/hooks/README.md) checks structure and links without
running recovery code or reading private inputs.
