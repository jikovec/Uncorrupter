# Handoff - 2026-08-05 - Stabilized Multi-Format Recovery

Final local convergence review: 2026-08-08

Tags: #agent/handoff #uncorrupter/recovery #uncorrupter/capabilities #uncorrupter/testing

## Outcome

The requested state/capability/format/improvement assessment is now implemented as a Spec Kit-backed `0.4.0` local candidate. It has a bounded streaming core, explicit handler/goal model, durable evidence/resume, executable machine-resolved capabilities, multi-format recovery paths, conditional validated external-tool paths, benchmarks, tests, and source-aligned documentation.

All local tasks in `specs/001-stabilize-multiformat-recovery/tasks.md` are complete. Only `T094`, exact-commit remote Windows/Linux/Python 3.11-3.13 CI/tool-matrix execution, remains open. It needs a committed SHA and explicit remote publication/CI authorization.

No Git or remote action was performed.

## Read First

1. `AGENTS.md`
2. `00_Index.md`
3. `docs/current-state.md`
4. `docs/decisions.md`
5. `docs/capabilities.generated.md`
6. `docs/CAPABILITIES-AND-ROADMAP.md`
7. `docs/BENCHMARK-GROUND-TRUTH.md`
8. `docs/architecture/ARCHITECTURE.md`
9. `docs/SOURCE-MAP.md`
10. `reports/2026-08-05-stabilized-multiformat-implementation.md`

## Current Product Truth

- Version: `0.4.0`, one source.
- Commands: `capabilities`, `scan`, `classify`, `recover`, `benchmark`, `report`.
- Goals: `repair`, `normalize`, `extract`, `preview`, `carve`.
- Outcome grades: all eight explicit grades are preserved in JSON, JSONL, CSV, and text.
- SQLite: schema version 2 with per-file durability and resume lineage.
- Public families: text, native archive, package document, PDF, JPEG, image, media, external archive, RTF, legacy Office.
- Valid archive/package/PDF/TIFF/media paths use streaming, bounded random access, or direct immutable tool paths.
- Corrupt reconstruction, large text, decoded rasters/frames, and child tools retain explicit resource boundaries.
- Benchmark: optional versioned labels, false-positive/negative and per-family metrics, main-process RSS sampling; child memory excluded.

## Conditional Tool Truth

On the reviewed Windows machine:

- FFmpeg and ffprobe `8.1.2` are available;
- real media normalize/extract/preview tests pass;
- qpdf, 7-Zip, LibreOffice, and `soffice` are unavailable.

Capabilities resolve dynamically:

- FFmpeg+ffprobe together enable copy-remux normalize, separate stream extraction, and one-frame preview after exact output validation and atomic publication;
- qpdf conditionally repairs/checks PDF and the native parser independently validates the exact candidate;
- 7-Zip conditionally lists/extracts 7z/RAR with bounded captured output;
- LibreOffice or Windows `soffice` conditionally produces a natively validated inert PDF preview for DOC/XLS/PPT.

Do not describe controlled fake-tool tests as real installed-tool proof.

## Verification Snapshot

- tool-disabled full suite: `154 passed, 1 skipped, 1 warning`;
- tool-present full suite: `155 passed, 1 warning`;
- focused real-FFmpeg media/recovery/integration suite: `21 passed`;
- focused CLI/capability/external-adapter suite: `30 passed`;
- streaming suite: `6 passed`;
- build: `0.4.0` sdist and wheel succeeded;
- compile: `src` and `tests` succeeded.

The duplicate-ZIP warning is intentional. The tool-disabled skip is the legacy FFmpeg recovery test and is not counted as tool-present proof. Consult the implementation report for commands and evidence boundaries.

## Non-Negotiable Behavioral Boundaries

- Never mutate an input path.
- Reject symlink/reparse sources and source identity drift.
- Keep output roots separate, contained, no-clobber, budgeted, and atomic.
- Inspection is read-only; publication occurs only in execution.
- Do not substitute unsupported goals.
- Validate the exact bytes later published; hash-correlate temporary tool output and final artifact.
- Encrypted input is reported, not cracked.
- Macros, scripts, HTML, OLE, relationships, and archive members remain inert.
- Valid TAR is not rewritten; preview/remux/extract remain narrower than full recovery.
- `preview_only` must not be upgraded to editable/full-fidelity recovery.
- A green test or workflow file is not release/deployment/live proof.

## Main Source Ownership

- core: `budgets.py`, `byte_source.py`, `paths.py`, `atomic.py`, `cancellation.py`, `events.py`, `process_runner.py`;
- coordination/evidence: `types.py`, `db.py`, `pipeline.py`, `cli.py`, `reporting.py`, `benchmarking.py`, `capabilities.py`;
- formats: `handlers/text.py`, `archive.py`, `package_document.py`, `pdf.py`, `image.py`, `legacy_media.py`, `media.py`, `external.py`;
- codecs/tools: `decoders.py`, `engines/`;
- evidence: `tests/fixtures.py`, `tests/mutations.py`, all `tests/test_*.py`, especially `test_streaming_handlers.py`, `test_benchmarking.py`, `test_determinism.py`, and lifecycle/CLI tests.

## Preserved Existing State

Do not overwrite, reset, clean, stage, or mix:

- user-owned `docs/OBSIDIAN.md` edits;
- concurrent declared-video/embedded-JPEG classifier work and `tests/test_classification.py`;
- `handoffs/2026-07-26-video-jpeg-misclassification-fix.md`;
- pre-existing `AGENTS.md` changes;
- `.uncorrupter-workspace/`, `output/`, and `single-input/` local data;
- any other unrelated dirty/untracked work visible at task start.

Refresh status and relevant diffs before editing because this handoff describes a dirty local candidate, not a clean commit.

## Verification Commands

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest -q -rs

Remove-Item Env:\UNCORRUPTER_DISABLE_EXTERNAL_TOOLS -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -q -rs

.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe -m json.tool .\docs\agent-index.json > $null
git diff --check
```

Run generated capability equality and Markdown link/fence validation after documentation changes. Record optional-tool identities and tool-disabled/tool-present runs separately.

## Remaining Work In Priority Order

1. After explicit authorization, commit a scoped candidate, push it, run the Windows/Linux/Python matrix, and correlate results to the exact SHA; do not mark `T094` complete earlier.
2. Build a licensed real-world corpus with expected recovered-content/artifact hashes and enough positive/negative samples for support thresholds.
3. Add renderer-backed PDF/Office page and semantic coverage in a genuine isolation boundary.
4. Run real qpdf/7-Zip/LibreOffice/optional-codec/isolation-wrapper matrices on Windows and Linux.
5. Measure child-process/whole-tree memory, CPU, and IO.
6. Deepen corrupt PDF/container, Office semantic, multipage/animation, media packet/frame/sample, metadata, and RAW recovery.
7. Add hostile-corpus fuzzing, supply-chain review, and independent defensive security assessment.
8. Decide release, signing, distribution, and support policy separately.

## Authorization Boundary

This implementation did not stage, commit, push, create a branch/PR, dispatch CI, tag, publish a package, create a release, deploy, or change remote settings. Future local work does not imply authority for those actions.
