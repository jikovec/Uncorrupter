from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from file_uncorrupter.budgets import ResourceLimits
from file_uncorrupter.cancellation import CancellationToken
from file_uncorrupter.db import (
    connect,
    fetch_resume_files,
    file_transaction,
    insert_attempt,
    insert_file,
    insert_output,
    source_identity_matches,
    start_run,
    transition_file,
    transition_run,
)
from file_uncorrupter.events import MachineEventWriter
from file_uncorrupter.handlers.base import RecoveryGoal
from file_uncorrupter.pipeline import RecoveryPipeline
from file_uncorrupter.reporting import build_final_manifest, write_attempts_csv, write_json_report, write_text_report
from file_uncorrupter.types import Artifact, Classification, DecodeResult, FileRecord, OutcomeGrade


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_multiformat_coordinator_preserves_source_and_publishes_atomic_text_artifacts(tmp_path):
    source_root = tmp_path / "input"
    output_root = tmp_path / "output"
    source_root.mkdir()
    source = source_root / "note.txt"
    source.write_bytes("Ahoj, bounded recovery.\n".encode("utf-8"))
    original_hash = _sha256(source)

    pipeline = RecoveryPipeline(limits=ResourceLimits(max_workers=1))
    execution = pipeline.process_path(
        source_root,
        source,
        output_root=output_root,
        goals=(RecoveryGoal.REPAIR,),
    )

    assert execution.status == "recovered"
    assert execution.classification is not None
    assert execution.classification.family == "text"
    assert execution.artifacts
    assert _sha256(source) == original_hash
    assert all(path.path.is_file() for path in execution.artifacts)
    assert all(path.path.resolve().is_relative_to(output_root.resolve()) for path in execution.artifacts)
    assert not list(output_root.rglob("*.tmp"))


def test_output_budget_stops_only_the_file_goal_and_leaves_no_temporary_artifact(tmp_path):
    source_root = tmp_path / "input"
    output_root = tmp_path / "output"
    source_root.mkdir()
    source = source_root / "note.txt"
    source.write_text("more than two bytes", encoding="utf-8")
    limits = ResourceLimits(max_workers=1, max_output_bytes=2)

    execution = RecoveryPipeline(limits=limits).process_path(
        source_root,
        source,
        output_root=output_root,
        goals=(RecoveryGoal.REPAIR,),
        limits=limits,
    )

    assert execution.status == "budget_exceeded"
    assert execution.goals[0].outcome.grade == "budget_exceeded"
    assert not [path for path in output_root.rglob("*") if path.is_file()]


def test_pre_cancelled_marker_returns_explicit_cancelled_analysis(tmp_path):
    source_root = tmp_path / "input"
    source_root.mkdir()
    source = source_root / "note.txt"
    source.write_text("cancel me", encoding="utf-8")
    marker = tmp_path / "cancel.marker"
    marker.touch()

    execution = RecoveryPipeline(limits=ResourceLimits(max_workers=1)).process_path(
        source_root,
        source,
        output_root=tmp_path / "output",
        goals=(RecoveryGoal.REPAIR,),
        cancellation=CancellationToken(marker),
    )

    assert execution.status == "cancelled"
    assert execution.error_code == "cancelled"
    assert not execution.artifacts


def test_per_file_savepoint_rollback_preserves_prior_durable_file(tmp_path):
    db_path = tmp_path / "run.sqlite3"
    with connect(db_path) as conn:
        run_id = start_run(conn, "recover", tmp_path, tmp_path / "out", "baseline-v2")
        conn.execute(
            "INSERT INTO files (run_id, relative_path, absolute_path, size, sha256, byte0_kind, status) VALUES (?, 'first', 'first', 0, '', 'unknown', 'scanned')",
            (run_id,),
        )
        conn.commit()
        with pytest.raises(RuntimeError):
            with file_transaction(conn, "second"):
                conn.execute(
                    "INSERT INTO files (run_id, relative_path, absolute_path, size, sha256, byte0_kind, status) VALUES (?, 'second', 'second', 0, '', 'unknown', 'scanned')",
                    (run_id,),
                )
                raise RuntimeError("synthetic failure")
        assert [row[0] for row in conn.execute("SELECT relative_path FROM files ORDER BY id")] == ["first"]


def test_resume_identity_and_final_manifest_are_deterministic_and_typed(tmp_path):
    source_root = tmp_path / "input"
    output_root = tmp_path / "output"
    source_root.mkdir()
    source = source_root / "note.txt"
    source.write_text("stable", encoding="utf-8")
    pipeline = RecoveryPipeline(limits=ResourceLimits(max_workers=1))
    execution = pipeline.process_path(source_root, source, output_root=output_root, goals=(RecoveryGoal.REPAIR,))

    with connect(tmp_path / "run.sqlite3") as conn:
        run_id = start_run(conn, "recover", source_root, output_root, "baseline-v2")
        transition_run(conn, run_id, "running")
        pipeline.persist_execution(conn, run_id, execution)
        transition_run(conn, run_id, "completed")
        prior = fetch_resume_files(conn, run_id)["note.txt"]
        manifest_a = build_final_manifest(conn, run_id)
        manifest_b = build_final_manifest(conn, run_id)

    assert source_identity_matches(prior, execution.record)
    assert manifest_a == manifest_b
    assert manifest_a["files"][0]["status"] == "recovered"
    assert manifest_a["files"][0]["artifacts"]


def test_every_outcome_grade_is_distinct_in_json_jsonl_csv_and_text_reports(tmp_path):
    db_path = tmp_path / "outcomes.sqlite3"
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    output_root.mkdir()
    grades = [grade.value for grade in OutcomeGrade]
    status_for_grade = {
        OutcomeGrade.VALIDATED_ORIGINAL.value: "recovered",
        OutcomeGrade.VALIDATED_NORMALIZED.value: "recovered",
        OutcomeGrade.PARTIAL_CONTENT.value: "partial",
        OutcomeGrade.PREVIEW_ONLY.value: "partial",
        OutcomeGrade.UNAVAILABLE_DEPENDENCY.value: "unavailable",
        OutcomeGrade.BUDGET_EXCEEDED.value: "budget_exceeded",
        OutcomeGrade.CANCELLED.value: "cancelled",
        OutcomeGrade.FAILED.value: "failed",
    }

    with connect(db_path) as conn:
        run_id = start_run(conn, "recover", input_root, output_root, "test-engine")
        transition_run(conn, run_id, "running")
        for index, grade in enumerate(grades):
            payload = grade.encode("utf-8")
            source_path = input_root / f"{index:02d}-{grade}.bin"
            source_path.write_bytes(payload)
            record = FileRecord(
                path=source_path,
                relative_path=Path(source_path.name),
                size=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                declared_kind="bin",
                byte0_kind="unknown",
                anywhere_kind="unknown",
            )
            file_id = insert_file(conn, run_id, record, Classification("test", grade, 1.0))
            ok = grade not in {
                OutcomeGrade.UNAVAILABLE_DEPENDENCY.value,
                OutcomeGrade.BUDGET_EXCEEDED.value,
                OutcomeGrade.CANCELLED.value,
                OutcomeGrade.FAILED.value,
            }
            decode = DecodeResult(ok=ok, decoder="outcome-fixture", error="" if ok else grade)
            attempt_id = insert_attempt(
                conn,
                run_id,
                file_id,
                None,
                decode,
                phase="repair",
                outcome_grade=grade,
            )
            artifact_path = output_root / f"{grade}.bin"
            artifact_path.write_bytes(payload)
            artifact = Artifact(
                artifact_type="diagnostics",
                path=artifact_path,
                sha256=hashlib.sha256(payload).hexdigest(),
                decoder="outcome-fixture",
                size=len(payload),
                fidelity_grade=grade,
                validation_state="fixture",
                published=True,
            )
            insert_output(conn, run_id, file_id, attempt_id, None, decode, artifact, None)
            transition_file(conn, file_id, status_for_grade[grade])
        transition_run(conn, run_id, "partial")

        json_path = tmp_path / "report.json"
        csv_path = tmp_path / "report.csv"
        text_path = tmp_path / "report.txt"
        manifest = write_json_report(conn, run_id, json_path)
        write_attempts_csv(conn, run_id, csv_path)
        write_text_report(conn, run_id, text_path)

    event_path = tmp_path / "events.jsonl"
    event_writer = MachineEventWriter(event_path)
    for grade in grades:
        event_writer.emit("goal.completed", {"outcome_grade": grade})

    json_grades = {
        artifact["fidelity_grade"]
        for item in manifest["files"]
        for artifact in item["artifacts"]
    }
    csv_grades = {row["outcome_grade"] for row in csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines())}
    jsonl_grades = {
        json.loads(line)["payload"]["outcome_grade"]
        for line in event_path.read_text(encoding="utf-8").splitlines()
    }
    text_report = text_path.read_text(encoding="utf-8")

    assert json_grades == set(grades)
    assert set(manifest["summary"]["by_outcome_grade"]) == set(grades)
    assert csv_grades == set(grades)
    assert jsonl_grades == set(grades)
    assert all(f"  {grade}: 1" in text_report for grade in grades)
