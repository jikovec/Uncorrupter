# Implementation Plan: Stabilized Multi-Format Recovery

**Branch**: 001-stabilize-multiformat-recovery | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from specs/001-stabilize-multiformat-recovery/spec.md

## Summary

Evolve the existing evidence-first JPEG/media prototype into a safe, deterministic multi-format recovery CLI. Preserve the current JPEG engine, replace whole-file orchestration with bounded byte sources and lazy candidate plans, publish artifacts atomically, version the SQLite evidence model, route work through declarative format handlers, and add native conservative handlers for text, ZIP/TAR/package documents, PDF, common image/container structures, and audio signatures. Complex proprietary formats use optional isolated-tool adapters with explicit unavailable and partial outcomes.

## Technical Context

**Language/Version**: Python 3.11 through 3.13

**Primary Dependencies**: Pillow as the only mandatory third-party runtime dependency; Python standard library for SQLite, ZIP, TAR, XML, CSV, JSON, hashing, concurrency, temporary files, and subprocess orchestration; optional FFmpeg/ffprobe, qpdf, 7z, unrar, and LibreOffice adapters

**Storage**: Versioned local SQLite evidence database plus an atomic filesystem artifact store

**Testing**: Pytest with generated deterministic fixtures, mutation helpers, CLI integration tests, subprocess fakes, resource attacks, migration tests, and optional-tool gates

**Target Platform**: Offline local CLI on Windows and Linux

**Project Type**: Single Python package and command-line application

**Performance Goals**: Stream-inspect a 1 GiB source below 256 MiB peak process memory; enforce configured time/byte/count limits; complete the bundled non-optional suite within 180 seconds on a typical workstation

**Constraints**: Immutable inputs, no-clobber default, deterministic results, no network dependency, safe path containment, no macro or active-content execution, no password cracking, bounded external processes, honest capability grades

**Scale/Scope**: Large local file trees and individual files up to configured limits; ten user stories and all format families named by the roadmap

## Constitution Check

The repository constitution is an unfilled template, so it imposes no executable gates. The governing constraints come from AGENTS.md and the approved specification:

- PASS: preserve the existing dirty worktree and do not edit unrelated docs/OBSIDIAN.md.
- PASS: retain current behavior unless a documented safety or correctness requirement changes it.
- PASS: treat corruption, hostile files, recovery integrity, and packaging as security-sensitive.
- PASS: use tests and evidence for every public capability.
- PASS: keep Spec Kit artifacts local-only under the already ignored specs and .specify state.

Post-design check: PASS. The design retains the current package shape, makes safety policies explicit, and avoids unnecessary services or cloud dependencies.

## Design Decisions

### Bounded Core

- Introduce immutable FileByteSource objects with bounded random reads, chunk iteration, streaming hashes, prefix/tail windows, and temporary materialization.
- Introduce CandidatePlan objects that reference source ranges and byte transformations. Existing eager Candidate objects remain a compatibility adapter for the JPEG engine during migration.
- Centralize ResourceLimits and BudgetTracker so every handler, candidate, extraction, decoder, and run consumes named budgets.

### Safe Publication

- Validate path relationships before a run starts.
- Reserve output names through a deterministic collision policy.
- Write regular artifacts to temporary siblings, validate and flush them, then publish using atomic replacement only when replacement was explicitly requested.
- Extract containers into new temporary directories, validate containment and budgets, then publish the directory or rebuilt container.

### Handler Registry

- Add one FormatHandler protocol and registry with detect, inspect, validate, plan, execute, and capability methods.
- Keep JPEG repair behind a legacy-engine adapter; route generic media through structural handlers and the bounded process adapter.
- Generate the capabilities command and capability-consistency tests from handler declarations.

### Evidence And Lifecycle

- Introduce schema version 2 with migration history, run lifecycle columns, source identity, file status, capability/tool snapshots, artifact relations, budget events, and machine events.
- Add deterministic path pseudonyms and a redacted report/event mode that never emits canonical source or workspace paths.
- Commit each file independently. Run-level transitions occur in their own transactions.
- Resume by run identifier and compare size, modification time, and streaming hash before reusing a completed file.
- External tools run from fresh temporary working directories with an allowlisted environment. An optional configured OS isolation wrapper is recorded, and a require-isolation policy fails closed if no wrapper is available.


### Format Strategy

- Text: loss-averse decoding and byte-offset span maps.
- ZIP: normal validation plus bounded local-header scanning and conservative reconstruction; safe member extraction is implemented by the application rather than extractall.
- TAR: sequential checksum/header analysis and safe regular-file extraction.
- Package documents: ZIP-derived part/relationship validation and separate content/media extraction.
- PDF: native bounded object/xref diagnostics and conservative trailer/xref candidate generation; qpdf/rendering stay optional.
- Images: native PNG/GIF/BMP/RIFF/TIFF structural analyzers plus Pillow validation; codec-dependent families report actual availability.
- Media: native container/audio header analyzers plus bounded FFmpeg/ffprobe remux, extraction, preview, and continuity telemetry.
- 7z/RAR/legacy Office: optional adapter-first support; no in-process parser for proprietary repair.

## Project Structure

### Documentation (this feature)

~~~text
specs/001-stabilize-multiformat-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── handler-protocol.md
│   ├── capability.schema.json
│   └── run-manifest.schema.json
├── checklists/
│   ├── requirements.md
│   └── recovery-quality.md
└── tasks.md
~~~

### Source Code (repository root)

~~~text
.github/workflows/
└── ci.yml

src/file_uncorrupter/
├── __init__.py
├── atomic.py
├── budgets.py
├── byte_source.py
├── capabilities.py
├── cancellation.py
├── cli.py
├── constants.py
├── db.py
├── events.py
├── paths.py
├── pipeline.py
├── process_runner.py
├── types.py
├── handlers/
│   ├── base.py
│   ├── registry.py
│   ├── legacy_media.py
│   ├── text.py
│   ├── archive.py
│   ├── package_document.py
│   ├── pdf.py
│   ├── image.py
│   ├── media.py
│   └── external.py
└── engines/
    ├── jpeg_v1.py
    └── compatibility modules

tests/
├── fixtures.py
├── mutations.py
├── test_atomic_and_paths.py
├── test_budgets_and_byte_source.py
├── test_capabilities.py
├── test_cli.py
├── test_db_migrations.py
├── test_run_lifecycle.py
├── test_text_handler.py
├── test_archive_handler.py
├── test_package_documents.py
├── test_pdf_handler.py
├── test_image_handlers.py
├── test_media_handlers.py
├── test_external_adapters.py
└── existing regression tests
~~~

**Structure Decision**: Retain the single-package src layout and existing engines. Add cross-cutting safety modules and a handlers package rather than replacing the proven JPEG logic or creating a service layer.

## Implementation Sequence

1. Packaging, version truth, baseline tests, and CI.
2. Budgets, byte source, cancellation, paths, atomic publication, and bounded subprocess runner.
3. Schema migration, run lifecycle, source identity, events, artifacts, and resume.
4. Handler/capability contracts and CLI surface.
5. Text vertical slice.
6. ZIP/TAR and package documents.
7. PDF.
8. Image structural handlers and codec-dependent capability truth.
9. Video/audio/container analyzers and external adapters.
10. Mutation corpus, benchmarks, docs, full verification, and convergence.

## Complexity Tracking

| Added Complexity | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Lazy candidate plans alongside eager JPEG candidates | Avoid large copies while preserving proven repair behavior | Immediate full JPEG rewrite would add regression risk |
| Handler registry | Public truth and format-specific safety/validation differ materially | One global extension map caused current overstatement and unknown-format gaps |
| Artifact graph and schema migration | Multi-output recovery and resumability require durable provenance | A single winning output cannot represent extracted pages, members, frames, and diagnostics |
| Optional isolated adapters | Some proprietary formats are impractical to repair natively | Claiming support without tools or embedding large parser dependencies would be misleading |
