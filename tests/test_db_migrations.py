from __future__ import annotations

import sqlite3

import pytest

from file_uncorrupter.db import (
    CURRENT_SCHEMA_VERSION,
    connect,
    insert_artifact_relation,
    insert_budget_event,
    insert_event,
    schema_version,
    start_run,
    transition_run,
)


def test_connect_applies_additive_schema_version_and_evidence_tables(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    raw = sqlite3.connect(path)
    raw.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY, command TEXT NOT NULL, created_at TEXT)")
    raw.commit()
    raw.close()

    with connect(path) as conn:
        assert schema_version(conn) == CURRENT_SCHEMA_VERSION
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert {"schema_meta", "events", "budget_events", "artifact_relations", "candidate_strategies"} <= tables


def test_run_lifecycle_enforces_terminal_state_and_records_timestamps(tmp_path):
    with connect(tmp_path / "runs.sqlite3") as conn:
        run_id = start_run(conn, "recover", tmp_path, tmp_path / "out", "baseline-v2")
        transition_run(conn, run_id, "running")
        transition_run(conn, run_id, "completed")
        row = conn.execute("SELECT state, started_at, finished_at FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert tuple(row) == ("completed", row["started_at"], row["finished_at"])
        assert row["started_at"] and row["finished_at"]
        with pytest.raises(ValueError, match="terminal"):
            transition_run(conn, run_id, "running")


def test_events_budgets_and_artifact_relations_are_persisted(tmp_path):
    with connect(tmp_path / "runs.sqlite3") as conn:
        run_id = start_run(conn, "recover", tmp_path, tmp_path / "out", "baseline-v2")
        event_id = insert_event(conn, run_id, "run.created", {"safe": True}, sequence=1)
        budget_id = insert_budget_event(
            conn,
            run_id,
            name="output_bytes",
            limit_value=10,
            consumed=11,
            outcome="exceeded",
        )
        relation_id = insert_artifact_relation(
            conn,
            run_id,
            child_output_id=None,
            relation_type="derived_from",
            parent_kind="source",
            parent_identifier="sha256:abc",
            locator={"start": 0, "end": 3},
        )

        assert event_id > 0
        assert budget_id > 0
        assert relation_id > 0
