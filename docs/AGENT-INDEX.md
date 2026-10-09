# Future-Agent Orientation

Last reconciled with source and local verification: 2026-08-08.

## Start Here

Read in this order before meaningful work:

1. [`AGENTS.md`](../AGENTS.md)
2. [`00_Index.md`](../00_Index.md)
3. [`docs/current-state.md`](current-state.md)
4. [`docs/decisions.md`](decisions.md)
5. [`docs/SOURCE-MAP.md`](SOURCE-MAP.md)
6. [`docs/CONNECTIONS.md`](CONNECTIONS.md)
7. [`docs/capabilities.generated.md`](capabilities.generated.md)
8. the relevant dated report and handoff
9. the source/tests for the behavior being changed

For format work, also read [Capabilities and roadmap](CAPABILITIES-AND-ROADMAP.md), [Architecture](architecture/ARCHITECTURE.md), [Security](security/SECURITY.md), and [Testing](testing/VERIFICATION.md).

## Latest orientation review

The [2026-09-09 project card](PROJECT-OVERVIEW.md#current-project-card--2026-09-09) reconciles the accessible dirty local candidate with committed main and records host runtime prerequisites. The verification date above belongs to historical implementation evidence. Use proportionate documentation checks for orientation-only changes; the full suite below applies to behavior work.

## Current Product Truth

- Package/runtime candidate: `0.4.0`, single source in `src/file_uncorrupter/__init__.py`.
- Python: 3.11+; defined CI matrix through 3.13 on Windows and Ubuntu.
- Product: local bounded recovery CLI for text, archives, packages/documents, PDF, images, audio/video containers, RTF, and conditional external adapters.
- Evidence: SQLite schema version 2, JSONL events, JSON manifest, CSV, and text.
- Public commands: `capabilities`, `scan`, `classify`, `recover`, `benchmark`, `report`.
- Public goals: `repair`, `normalize`, `extract`, `preview`, `carve`.
- Capability authority: registered handler records and the live `capabilities` command.
- Checked documentation baseline: external tools disabled, `docs/capabilities.generated.md`.
- Current evidence level: implemented and locally tested with synthetic fixtures; not deployed or live-verified.

## Hard Safety Rules

- Preserve source immutability and no-clobber atomic publication.
- Do not bypass `FileByteSource`, `BudgetTracker`, `CancellationToken`, `AtomicArtifactWriter`, or `run_process` for new handler work.
- Do not add an extension to public capabilities without an owning handler, operation levels, fixtures/mutations, validators, limits, artifact semantics, and fidelity boundary.
- Do not silently substitute one recovery goal for another.
- Do not call a decoder/tool success full recovery without validating the exact published artifact.
- Never execute embedded active content or guess passwords.
- Keep optional-tool-absent behavior functional and deterministic.
- Preserve per-file persistence and resume history.
- Do not store raw source bytes in SQLite/events/reports.
- Keep `.obsidian/` local/ignored and `.agents/`/`.specify/` local-only.
- Do not stage, commit, push, create PRs, dispatch workflows, release, deploy, or change remote settings without explicit authorization for that action.

## Dirty Worktree And Authored-Scope Boundary

At the end of the stabilization work, the repository already contained or retained unrelated/user-owned local state:

- `docs/OBSIDIAN.md` user-owned edits;
- the declared-video/embedded-JPEG classifier change, `tests/test_classification.py`, and `handoffs/2026-07-26-video-jpeg-misclassification-fix.md`;
- `.uncorrupter-workspace/`, `output/`, and `single-input/` local generated/test material;
- local-only `.agents/`, `.specify/`, and ignored editor/config paths.

Never reset, clean, overwrite, stage, or mix these merely to simplify a task. Refresh `git status` and relevant diffs before editing.

## Key Source Ownership

| Area | Owner |
| --- | --- |
| CLI/lifecycle/resume/exit policy | `src/file_uncorrupter/cli.py` |
| Coordinator/persistence bridge | `src/file_uncorrupter/pipeline.py` |
| Immutable sources | `byte_source.py`, `intake.py` |
| Limits/cancellation | `budgets.py`, `cancellation.py` |
| Paths/publication | `paths.py`, `atomic.py` |
| Optional tools | `process_runner.py`, `decoders.py` |
| Capabilities/registry | `capabilities.py`, `handlers/base.py`, `handlers/registry.py` |
| Format behavior | `handlers/*.py` |
| Evidence/migrations | `db.py` |
| Events/reports | `events.py`, `reporting.py` |
| Benchmark labels/metrics/RSS | `benchmarking.py`, `cli.py`, `reporting.py` |
| Fixtures/mutations | `tests/fixtures.py`, `tests/mutations.py`, `tests/test_mutation_inventory.py` |

Use [SOURCE-MAP.md](SOURCE-MAP.md) for the complete source-to-test map.

## Required Verification Pattern

Start focused, then run the full deterministic suite:

```powershell
$env:UNCORRUPTER_DISABLE_EXTERNAL_TOOLS = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -p no:cacheprovider -q
python -m compileall -q src tests
python -m build
python -m json.tool .\docs\agent-index.json > $null
git diff --check
```

Run optional-tool-present checks separately and report exact versions/skips. Validate capability/doc equality after handler changes. See [testing/VERIFICATION.md](testing/VERIFICATION.md).

## Known Open Gates

- GitHub Actions has a workflow definition but exact-commit remote execution is unverified in the stabilization report.
- The corpus is synthetic and representative, not a broad labeled real-world benchmark.
- False-positive/false-negative metrics require explicit ground-truth labels; the implemented RSS sampler excludes child-process memory.
- Public archive, package, PDF, TIFF/image, and media paths stream, but corrupt reconstruction, large text, decoded rasters/frames, and some third-party codecs retain bounded memory/disk limitations.
- Media normalize/extract/preview is conditional on both FFmpeg and ffprobe; keep tool-absent behavior explicit and validate the exact published hash.
- PDF renderer-backed coverage, optional image codecs, and real qpdf/7z/RAR/LibreOffice tool-present matrices need deeper validation.
- No bundled sandbox or independent defensive security audit exists.
- No release/publication/deployment has been performed.

## Documentation Update Obligations

When behavior changes, update all affected surfaces:

- handler capability record and tests;
- `docs/capabilities.generated.md`;
- README/CLI/current state/roadmap as applicable;
- architecture/source/connection maps if ownership or flow changes;
- security/testing docs if a boundary or gate changes;
- `docs/agent-index.json` for paths, commands, tags, safety rules, or risks;
- a dated report and handoff for substantive work.

Do not update `docs/OBSIDIAN.md` unless the task directly requires it and existing user edits are reconciled.

## Evidence And Handoff

- Current implementation report: [`reports/2026-08-05-stabilized-multiformat-implementation.md`](../reports/2026-08-05-stabilized-multiformat-implementation.md)
- Current handoff: [`handoffs/2026-08-05-stabilized-multiformat-recovery.md`](../handoffs/2026-08-05-stabilized-multiformat-recovery.md)
- Earlier classification handoff: [`handoffs/2026-07-26-video-jpeg-misclassification-fix.md`](../handoffs/2026-07-26-video-jpeg-misclassification-fix.md)
- Reports index: [`reports/INDEX.md`](../reports/INDEX.md)
- Handoffs index: [`handoffs/INDEX.md`](../handoffs/INDEX.md)

## Obsidian Conventions

The repository root may be opened as a local-first plaintext vault. Normal Markdown links are canonical. `.obsidian/` remains ignored and must not be repurposed for cloud sync, accounts, or encryption setup. See [OBSIDIAN.md](OBSIDIAN.md).

## AI task workflow

See the [project AI workflow](agent-workflow.md) for completion rules, existing commands, local environment actions and delivery boundaries.
