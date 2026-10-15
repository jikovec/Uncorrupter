# Tasks: Stabilized Multi-Format Recovery

**Input**: Design documents from specs/001-stabilize-multiformat-recovery/

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by the specification. Story tests are written before their implementations.

**Organization**: Tasks are grouped by independently testable user story.

## Format: [ID] [P?] [Story] Description

- **[P]**: May proceed independently because it uses different files and has no incomplete dependency.
- **[Story]**: Maps the task to its specification user story.

## Phase 1: Setup And Reproducibility

**Purpose**: Establish version truth, declared development dependencies, CI scaffolding, and deterministic fixture helpers.

- [x] T001 Reconcile authoritative package/runtime version and declare development dependencies in pyproject.toml and src/file_uncorrupter/__init__.py
- [x] T002 [P] Add Windows/Linux and Python 3.11-3.13 quality workflow with tool-present/tool-absent jobs in .github/workflows/ci.yml
- [x] T003 [P] Add deterministic format fixture builders in tests/fixtures.py
- [x] T004 [P] Add reusable corruption mutation helpers in tests/mutations.py
- [x] T005 Record the pre-change passing baseline and installation contract in reports/2026-08-05-stabilized-multiformat-implementation.md

---

## Phase 2: Foundational Bounded Recovery Core

**Purpose**: Build the shared contracts that block every format story.

**Critical**: No format handler is implemented before this phase passes.

- [x] T006 [P] Add failing resource-budget tests in tests/test_budgets_and_byte_source.py
- [x] T007 Implement immutable resource limits and hierarchical budget tracking in src/file_uncorrupter/budgets.py
- [x] T008 Add failing streaming/random-access/source-change and 1 GiB sparse-memory regression tests in tests/test_budgets_and_byte_source.py
- [x] T009 Implement bounded file byte sources, streaming hashes, slices, and materialization in src/file_uncorrupter/byte_source.py
- [x] T010 [P] Add failing path containment, collision, and atomic-publication tests in tests/test_atomic_and_paths.py
- [x] T011 Implement canonical path-layout validation and safe relative-name handling in src/file_uncorrupter/paths.py
- [x] T012 Implement temporary-sibling atomic artifact publication with fail/suffix/replace policies in src/file_uncorrupter/atomic.py
- [x] T013 [P] Add failing timeout, output-limit, cancellation, cleanup, tool-version, minimal-environment, and required-isolation tests in tests/test_process_runner.py
- [x] T014 Implement the unified bounded subprocess runner, minimal environment, temporary working directory, and optional required isolation wrapper in src/file_uncorrupter/process_runner.py
- [x] T015 [P] Implement cancellation tokens and file-marker cancellation in src/file_uncorrupter/cancellation.py
- [x] T016 [P] Implement deterministic JSONL machine events in src/file_uncorrupter/events.py
- [x] T017 Extend source, candidate-plan, attempt, artifact, outcome, and tool evidence types in src/file_uncorrupter/types.py
- [x] T018 [P] Add failing schema migration, lifecycle, artifact-relation, event, and budget persistence tests in tests/test_db_migrations.py
- [x] T019 Implement explicit schema versioning and additive evidence/lifecycle migrations in src/file_uncorrupter/db.py
- [x] T020 Define the format handler, capability, inspection, and execution contracts in src/file_uncorrupter/handlers/base.py
- [x] T021 Implement the deterministic handler registry in src/file_uncorrupter/handlers/registry.py and src/file_uncorrupter/handlers/__init__.py
- [x] T022 Implement the legacy JPEG/media compatibility handler in src/file_uncorrupter/handlers/legacy_media.py
- [x] T023 Refactor engine payload deduplication to separate content identity from strategy identity in src/file_uncorrupter/types.py and src/file_uncorrupter/engines/media_v2.py

**Checkpoint**: Foundational unit tests pass and existing JPEG tests remain green.

---

## Phase 3: User Story 1 - Recover Untrusted Files Safely (Priority: P1)

**Goal**: Immutable inputs, bounded execution, safe path layout, and atomic no-clobber outputs.

**Independent Test**: Run path, collision, source-change, oversized, symlink, and decoder-budget fixtures and demonstrate no source/output mutation or path escape.

- [x] T024 [P] [US1] Add end-to-end safety and immutable-input tests in tests/test_safe_recovery.py
- [x] T025 [US1] Refactor intake to deterministic discovery and streaming source records in src/file_uncorrupter/intake.py
- [x] T026 [US1] Integrate path validation, budgets, candidate plans, and atomic publication into src/file_uncorrupter/pipeline.py
- [x] T027 [US1] Harden workspace blob/config/report writes with atomic no-clobber behavior in src/file_uncorrupter/workspace.py
- [x] T028 [US1] Route Pillow and FFmpeg artifacts through bounded validation and publication in src/file_uncorrupter/decoders.py
- [x] T029 [US1] Persist source-change, collision, budget, and publication evidence in src/file_uncorrupter/db.py

**Checkpoint**: User Story 1 passes independently.

---

## Phase 4: User Story 2 - Run, Resume, Inspect, And Cancel Recovery (Priority: P1)

**Goal**: Durable lifecycle, per-file commits, cancellation, deterministic bounded workers, and safe resume.

**Independent Test**: Cancel a mixed run, inspect state/events, resume it, reuse unchanged completed files, and reject or reprocess changed sources.

- [x] T030 [P] [US2] Add failing lifecycle, cancellation, per-file durability, resume, and changed-input tests in tests/test_run_lifecycle.py
- [x] T031 [US2] Implement run/file transitions, resume queries, and bounded per-file transactions in src/file_uncorrupter/db.py
- [x] T032 [US2] Implement deterministic run coordination, cancellation checkpoints, and bounded worker execution in src/file_uncorrupter/pipeline.py
- [x] T033 [US2] Emit lifecycle, file, candidate, tool, budget, and artifact events through src/file_uncorrupter/events.py
- [x] T034 [US2] Add resume, cancellation, worker, changed-input, and complete-limit options in src/file_uncorrupter/cli.py
- [x] T035 [US2] Generate durable final run manifests, resumed-run summaries, and deterministic path-redacted reports in src/file_uncorrupter/reporting.py

**Checkpoint**: User Story 2 passes independently.

---

## Phase 5: User Story 3 - Know Exactly What Is Supported (Priority: P1)

**Goal**: Executable capability truth, explicit goals, and distinct scan/classify/recover behavior.

**Independent Test**: Compare capability output against registered handlers and fixture evidence with optional tools present and absent.

- [x] T036 [P] [US3] Add failing capability, goal, scan/classify distinction, and CLI exit-code tests in tests/test_capabilities.py and tests/test_cli.py
- [x] T037 [US3] Implement capability records, availability resolution, and JSON/text manifest generation in src/file_uncorrupter/capabilities.py
- [x] T038 [US3] Extend format constants, suffix/media mappings, and signature declarations in src/file_uncorrupter/constants.py
- [x] T039 [US3] Refactor signature detection to bounded windows and all registered format signatures in src/file_uncorrupter/signature_index.py
- [x] T040 [US3] Refactor classification to consume independent extension/signature/structure evidence in src/file_uncorrupter/classification.py
- [x] T041 [US3] Add capabilities command, explicit recovery goals, meaningful exit policies, and distinct scan/classify behavior in src/file_uncorrupter/cli.py
- [x] T042 [US3] Add a capability-evidence consistency gate in tests/test_capabilities.py

**Checkpoint**: User Story 3 passes independently.

---

## Phase 6: User Story 4 - Recover Text And Structured Text (Priority: P2)

**Goal**: Loss-averse text recovery with byte-offset provenance and bounded structure diagnostics.

**Independent Test**: Recover mixed encodings, invalid spans, binary contamination, and truncated JSON/XML/CSV/HTML/Markdown without invented text.

- [x] T043 [P] [US4] Add failing UTF-8/16/32, Windows-1252, ISO-8859-1, TXT/MD/log/CSV/JSON/XML/HTML recovery and span-map tests in tests/test_text_handler.py
- [x] T044 [US4] Implement enumerated encoding analysis, byte-preserving spans, optional normalization, and JSON/XML/CSV/HTML/Markdown structure diagnostics in src/file_uncorrupter/handlers/text.py
- [x] T045 [US4] Register text families and route text goals through src/file_uncorrupter/handlers/registry.py and src/file_uncorrupter/pipeline.py
- [x] T046 [US4] Persist text span maps and diagnostic artifacts in src/file_uncorrupter/db.py and src/file_uncorrupter/reporting.py

**Checkpoint**: User Story 4 passes independently.

---

## Phase 7: User Story 5 - Recover Archives And Package Documents (Priority: P2)

**Goal**: Safe ZIP/TAR recovery and part-aware Open XML/OpenDocument validation/extraction.

**Independent Test**: Handle valid, truncated, missing-directory, CRC, traversal, link/device, duplicate, encrypted, nested, and expansion fixtures within limits.

- [x] T047 [P] [US5] Add failing ZIP/TAR reconstruction, containment, checksum, duplicate, encryption, and bomb tests in tests/test_archive_handler.py
- [x] T048 [US5] Implement ZIP central/local-header analysis, conservative reconstruction, and safe streaming extraction in src/file_uncorrupter/handlers/archive.py
- [x] T049 [US5] Implement TAR sequential-header salvage and contained regular-member extraction in src/file_uncorrupter/handlers/archive.py
- [x] T050 [P] [US5] Add failing DOCX/XLSX/PPTX/ODT/ODS/ODP package and part-extraction tests in tests/test_package_documents.py
- [x] T051 [US5] Implement package type, manifest/content-type, required-part, relationship, macro, and active-content validation in src/file_uncorrupter/handlers/package_document.py
- [x] T052 [US5] Implement conservative package rebuild and separate text/media/attachment artifacts in src/file_uncorrupter/handlers/package_document.py
- [x] T053 [US5] Register archive/package handlers and persist member/part relations in src/file_uncorrupter/handlers/registry.py, src/file_uncorrupter/pipeline.py, and src/file_uncorrupter/db.py

**Checkpoint**: User Story 5 passes independently.

---

## Phase 8: User Story 6 - Recover PDF Content Conservatively (Priority: P3)

**Goal**: Bounded native PDF diagnostics, conservative cross-reference recovery, extraction, and optional tool validation.

**Independent Test**: Handle prefixed, missing-EOF, broken-startxref, missing-xref, orphan-object, page-tree, stream, and optional-tool fixtures.

- [x] T054 [P] [US6] Add failing PDF structure, repair, extraction, timeout, and unavailable-tool tests in tests/test_pdf_handler.py
- [x] T055 [US6] Implement bounded PDF token/object/stream/xref/trailer/page-tree analysis in src/file_uncorrupter/handlers/pdf.py
- [x] T056 [US6] Implement conservative header/EOF/xref candidates and text/image/attachment diagnostics in src/file_uncorrupter/handlers/pdf.py
- [x] T057 [US6] Add optional qpdf validation/repair through src/file_uncorrupter/process_runner.py and src/file_uncorrupter/handlers/pdf.py
- [x] T058 [US6] Register PDF capabilities and artifact relations in src/file_uncorrupter/handlers/registry.py, src/file_uncorrupter/pipeline.py, and src/file_uncorrupter/db.py

**Checkpoint**: User Story 6 passes independently.

---

## Phase 9: User Story 7 - Recover Images With Format-Aware Fidelity (Priority: P3)

**Goal**: Structural PNG/GIF/BMP/RIFF/TIFF recovery and honest codec-dependent image capabilities.

**Independent Test**: Mutate lengths, checksums, trailers, offsets, frame/page chains, suffixes, and codec availability for every public image family.

- [x] T059 [P] [US7] Add failing PNG/GIF/BMP/WebP/TIFF/HEIF/AVIF/JP2/RAW structure and fidelity tests in tests/test_image_handlers.py
- [x] T060 [US7] Implement bounded PNG chunk analysis, CRC repair, and trailer recovery in src/file_uncorrupter/handlers/image.py
- [x] T061 [US7] Implement GIF block, BMP header, RIFF/WebP chunk, and TIFF IFD analyzers and conservative repairs in src/file_uncorrupter/handlers/image.py
- [x] T062 [US7] Implement codec-dependent HEIF/AVIF/JP2/RAW inspection/preview capability resolution in src/file_uncorrupter/handlers/image.py
- [x] T063 [US7] Preserve animation/multipage output when possible and label first-frame derivatives as previews in src/file_uncorrupter/decoders.py
- [x] T064 [US7] Normalize image artifact suffixes and integrate image handlers in src/file_uncorrupter/handlers/registry.py and src/file_uncorrupter/pipeline.py

**Checkpoint**: User Story 7 passes independently.

---

## Phase 10: User Story 8 - Recover Video, Audio, And Complex Containers (Priority: P3)

**Goal**: Structural container/audio analysis with bounded FFmpeg-assisted remux, extraction, preview, and continuity evidence.

**Independent Test**: Exercise prefixed, truncated, missing-index, discontinuity, timeout, tool-absent, and output-failure scenarios.

- [x] T065 [P] [US8] Add failing MP4/MOV/EBML/AVI/MPEG/FLV/ASF and WAV/MP3/FLAC/AAC/Ogg tests in tests/test_media_handlers.py
- [x] T066 [US8] Implement MP4 box, EBML, RIFF/AVI, MPEG-TS/PS, FLV, ASF, and audio header analyzers in src/file_uncorrupter/handlers/media.py
- [x] T067 [US8] Refactor all media probe/remux/preview/frame/audio extraction through src/file_uncorrupter/process_runner.py and src/file_uncorrupter/decoders.py
- [x] T068 [US8] Record stream, timing, continuity, decoded coverage, warning, and fidelity evidence in src/file_uncorrupter/handlers/media.py
- [x] T069 [US8] Register media/audio handlers and persist frame/stream artifact relations in src/file_uncorrupter/handlers/registry.py, src/file_uncorrupter/pipeline.py, and src/file_uncorrupter/db.py

**Checkpoint**: User Story 8 passes independently.

---

## Phase 11: User Story 9 - Handle TAR, 7z, RAR, And Legacy Office Honestly (Priority: P4)

**Goal**: Native TAR plus isolated adapter-first support for complex archives and legacy documents.

**Independent Test**: Exercise tool-present/tool-absent, encrypted, multi-volume, solid, macro, conversion, timeout, and containment outcomes.

- [x] T070 [P] [US9] Add failing 7z/RAR/legacy Office adapter and safety tests in tests/test_external_adapters.py
- [x] T071 [US9] Implement bounded 7z and RAR list/extract adapters in src/file_uncorrupter/handlers/external.py
- [x] T072 [US9] Implement bounded legacy Office/RTF inspection and optional conversion adapter in src/file_uncorrupter/handlers/external.py
- [x] T073 [US9] Register external capabilities with tool, encryption, multivolume, solid, macro, and conversion boundaries in src/file_uncorrupter/handlers/registry.py

**Checkpoint**: User Story 9 passes independently.

---

## Phase 12: User Story 10 - Reproduce And Govern Recovery Quality (Priority: P1)

**Goal**: Deterministic corpus, CLI/package tests, benchmark metrics, CI, and documentation consistency.

**Independent Test**: Install cleanly, run all matrix-equivalent local gates, repeat the mutation corpus, compare manifests, and build the package.

- [x] T074 [P] [US10] Add comprehensive parser, path, exit-code, event, report, and command integration tests in tests/test_cli.py
- [x] T075 [P] [US10] Expand mutation coverage and format evidence inventory in tests/mutations.py and tests/fixtures.py
- [x] T076 [US10] Add deterministic recovery/fidelity/runtime/memory/expansion/crash/timeout/budget benchmark metrics in src/file_uncorrupter/reporting.py and src/file_uncorrupter/cli.py
- [x] T077 [P] [US10] Add package build and single-version-source tests in tests/test_packaging.py
- [x] T078 [US10] Finalize CI packaging, capability, documentation, and optional-tool gates in .github/workflows/ci.yml
- [x] T079 [US10] Add generated capability/documentation drift checks in tests/test_capabilities.py

**Checkpoint**: User Story 10 passes independently.

---

## Phase 13: Polish, Documentation, And Full Verification

**Purpose**: Close cross-cutting gaps and leave durable evidence.

- [x] T080 Run and fix the complete test suite described by specs/001-stabilize-multiformat-recovery/quickstart.md
- [x] T081 Update usage, safety defaults, commands, and honest format support in README.md and docs/api/CLI.md
- [x] T082 Update current state, project overview, roadmap completion state, architecture, source map, and connection map in docs/current-state.md, docs/PROJECT-OVERVIEW.md, docs/CAPABILITIES-AND-ROADMAP.md, docs/architecture/ARCHITECTURE.md, docs/SOURCE-MAP.md, and docs/CONNECTIONS.md
- [x] T083 Update security, testing, setup, commands, changelog, agent index, and machine index in docs/security/SECURITY.md, docs/testing/VERIFICATION.md, docs/testing.md, docs/setup/DEVELOPMENT.md, docs/commands.md, docs/releases/CHANGELOG.md, docs/AGENT-INDEX.md, and docs/agent-index.json
- [x] T084 Complete implementation evidence and remaining-risk accounting in reports/2026-08-05-stabilized-multiformat-implementation.md
- [x] T085 Add a dated future-agent handoff and index it in handoffs/2026-08-05-stabilized-multiformat-recovery.md and handoffs/INDEX.md
- [x] T086 Validate JSON, Markdown links, code fences, package build, capability consistency, git diff hygiene, and authored-scope boundaries across the repository

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 establishes install and test scaffolding.
- Phase 2 blocks all user stories.
- User Stories 1-3 stabilize shared operation and block format publication.
- Text, archives/packages, PDF, images, media, and external adapters can proceed after User Story 3.
- User Story 10 and polish depend on all selected format stories.

### User Story Dependencies

- US1 depends on the bounded core only.
- US2 depends on US1 publication and evidence rules.
- US3 depends on foundational handler contracts and must complete before new public formats.
- US4 is the first independent new-handler vertical slice.
- US5 depends on US1 and US3; package documents depend on ZIP within US5.
- US6 depends on US1 and US3.
- US7 depends on US1 and US3 while retaining JPEG compatibility.
- US8 depends on US1, US2 cancellation, and the bounded process runner.
- US9 depends on archive safety and the bounded process runner.
- US10 depends on every public handler and lifecycle behavior.

## Parallel Opportunities

- Setup fixture and CI tasks marked [P] touch independent files.
- Foundational test files can be authored independently before their corresponding modules.
- After US3, the text, archive, PDF, image, and media test files are independent.
- Documentation files in the final phase can be reviewed independently after implementation truth is stable.

## Implementation Strategy

### Safety MVP

1. Complete Setup and Foundational phases.
2. Complete US1, US2, and US3.
3. Re-run all existing JPEG/media tests.
4. Only then publish new format capabilities.

### Incremental Format Delivery

1. Text
2. ZIP/TAR and package documents
3. PDF
4. Images
5. Video/audio
6. External adapters
7. Full corpus and documentation convergence

## Notes

- Completed tasks must be marked [x] in this file.
- Existing user-owned docs/OBSIDIAN.md changes remain untouched.
- No task authorizes commit, push, branch mutation, release, deployment, or destructive input handling.

## Phase 14: Convergence

- [x] T087 Complete cancellation-aware optional qpdf recovery output, atomic publication, and exact repaired-artifact validation in src/file_uncorrupter/handlers/pdf.py and tests/test_pdf_handler.py per FR-045 and T057
- [x] T088 Integrate FFmpeg remux, preview, frame, and audio extraction as explicit handler plans with atomic budgeted publication and exact output validation in src/file_uncorrupter/handlers/media.py and src/file_uncorrupter/decoders.py per FR-053 through FR-056 and T067
- [x] T089 Persist media stream, timing, timestamp continuity, decoded coverage, warning, tool, artifact-relation, and fidelity evidence for public media goals in src/file_uncorrupter/handlers/media.py, src/file_uncorrupter/pipeline.py, and src/file_uncorrupter/db.py per FR-055 and T068
- [x] T090 Implement and validate a bounded isolated legacy DOC/XLS/PPT conversion/extraction adapter, or keep every conversion goal unavailable with executable tool-present evidence, in src/file_uncorrupter/handlers/external.py and tests/test_external_adapters.py per FR-057 and T072
- [x] T091 Add labeled fixture-group ground truth, false-positive calculation, process peak-memory sampling, and per-group benchmark aggregation in src/file_uncorrupter/reporting.py, src/file_uncorrupter/cli.py, and benchmark tests per FR-063, SC-015, and T076
- [x] T092 Expand the fixture/mutation inventory from one representative variant per family to every public variant as applicable, including valid suffix/media-type checks and explicit coverage-gap failures, in tests/fixtures.py, tests/mutations.py, and tests/test_mutation_inventory.py per FR-061, SC-009, and SC-010
- [x] T093 Add a two-independent-run determinism test comparing normalized manifest ordering, selected artifact identities, strategy order, and hashes while excluding run IDs/timestamps in tests/test_run_lifecycle.py per FR-062 and SC-007
- [ ] T094 Execute clean-install Windows/Linux Python 3.11-3.13 and optional-tool-present/absent gates on an exact commit, record all skip/tool identities, and repair repository-caused failures without converting workflow definition into execution proof per SC-001 and SC-002 (external exact-commit gate)
- [x] T095 Add exhaustive JSON/JSONL/CSV/text assertions for every outcome grade and selectable exit policy in tests/test_cli.py and tests/test_run_lifecycle.py per SC-013 and SC-014
- [x] T096 Replace remaining bounded whole-file materialization in archive, package, PDF, TIFF/image, and media handlers with incremental parsing where practical, retaining explicit materialization fallback limits and memory regressions per FR-009 and SC-017
