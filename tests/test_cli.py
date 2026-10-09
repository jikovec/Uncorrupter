from __future__ import annotations

import json
import sqlite3

import pytest

from file_uncorrupter.cli import EXIT_FATAL, EXIT_NO_RESULTS, EXIT_OK, EXIT_PARTIAL, _exit_for_summary, main


def _common(input_root, db_path, workspace):
    return [
        str(input_root),
        "--all-files",
        "--db",
        str(db_path),
        "--workspace-root",
        str(workspace),
        "--workers",
        "1",
        "--quiet",
    ]


def test_capabilities_command_emits_quality_gated_json(capsys, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    assert main(["capabilities", "--format", "json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["quality_gate"]["passed"] is True
    assert {record["family"] for record in payload["capabilities"]} >= {
        "archive", "external_archive", "image", "jpeg", "legacy_office", "media",
        "package_document", "pdf", "rtf", "text",
    }


def test_scan_and_classify_have_distinct_persisted_behavior(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    input_root.mkdir()
    (input_root / "note.txt").write_text("hello", encoding="utf-8")

    scan_db = tmp_path / "scan.sqlite3"
    assert main(["scan", *_common(input_root, scan_db, tmp_path / "scan-work")]) == EXIT_OK
    capsys.readouterr()
    with sqlite3.connect(scan_db) as conn:
        scan_row = conn.execute("SELECT status, classification_family FROM files").fetchone()
    assert scan_row == ("scanned", None)

    classify_db = tmp_path / "classify.sqlite3"
    assert main(["classify", *_common(input_root, classify_db, tmp_path / "classify-work")]) == EXIT_OK
    capsys.readouterr()
    with sqlite3.connect(classify_db) as conn:
        classify_row = conn.execute("SELECT status, classification_family FROM files").fetchone()
    assert classify_row == ("classified", "text")


def test_recover_goal_writes_redacted_manifest_events_and_normalized_artifact(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    (input_root / "note.txt").write_bytes(b"one\r\ntwo\rthree\n")
    db_path = tmp_path / "run.sqlite3"

    code = main([
        "recover",
        *_common(input_root, db_path, tmp_path / "workspace"),
        str(output_root),
        "--goal",
        "normalize",
        "--redact-paths",
    ])
    summary = json.loads(capsys.readouterr().out)

    assert code == EXIT_OK
    assert summary["state"] == "completed"
    assert summary["by_status"] == {"recovered": 1}
    normalized = output_root / "note.txt.recovered" / "normalize" / "normalized.txt"
    assert normalized.read_bytes() == b"one\ntwo\nthree\n"
    manifest_path = tmp_path / "workspace" / "reports" / "run-000001.manifest.json"
    events_path = tmp_path / "workspace" / "reports" / "run-000001.events.jsonl"
    manifest = manifest_path.read_text(encoding="utf-8")
    events = events_path.read_text(encoding="utf-8")
    for canonical in (str(input_root.resolve()), str(output_root.resolve()), str((tmp_path / "workspace").resolve())):
        assert canonical not in manifest
        assert canonical not in events
    assert "source:" in manifest
    assert "source:" in events


def test_unsafe_overlap_fails_before_database_creation(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    input_root.mkdir()
    (input_root / "note.txt").write_text("safe source", encoding="utf-8")
    db_path = tmp_path / "run.sqlite3"

    code = main([
        "recover",
        *_common(input_root, db_path, tmp_path / "workspace"),
        str(input_root / "output"),
    ])

    assert code == EXIT_FATAL
    assert "overlaps input_root" in capsys.readouterr().err
    assert not db_path.exists()


def test_resume_skips_unchanged_and_aborts_changed_input(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    workspace = tmp_path / "workspace"
    db_path = tmp_path / "run.sqlite3"
    input_root.mkdir()
    source = input_root / "note.txt"
    source.write_text("first", encoding="utf-8")
    base = ["recover", *_common(input_root, db_path, workspace), str(output_root)]

    assert main(base) == EXIT_OK
    capsys.readouterr()
    assert main([*base, "--resume", "1"]) == EXIT_OK
    capsys.readouterr()
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT status FROM files WHERE run_id = 2").fetchone()[0] == "skipped"

    source.write_text("changed", encoding="utf-8")
    assert main([*base, "--resume", "1"]) == EXIT_FATAL
    capsys.readouterr()
    with sqlite3.connect(db_path) as conn:
        run = conn.execute("SELECT state, fatal_error FROM runs WHERE id = 3").fetchone()
        file_status = conn.execute("SELECT status, error_code FROM files WHERE run_id = 3").fetchone()
    assert run[0] == "failed"
    assert "resume input changed" in run[1]
    assert file_status == ("failed", "resume_input_changed")

    assert main([*base, "--resume", "1", "--changed-input-policy", "reprocess"]) == EXIT_OK
    capsys.readouterr()
    assert (output_root / "_resumed" / "run-000004" / "note.txt.recovered" / "repair").is_dir()


def test_no_results_exit_policy_is_selectable(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "empty"
    input_root.mkdir()
    db_path = tmp_path / "run.sqlite3"
    workspace = tmp_path / "workspace"

    strict = ["recover", *_common(input_root, db_path, workspace), str(tmp_path / "out-one")]
    assert main(strict) == EXIT_NO_RESULTS
    capsys.readouterr()
    report_only = [
        "recover", *_common(input_root, db_path, workspace), str(tmp_path / "out-two"),
        "--exit-policy", "report-only",
    ]
    assert main(report_only) == EXIT_OK
    capsys.readouterr()


@pytest.mark.parametrize(
    ("summary", "policy", "final_state", "expected"),
    [
        ({"total_files": 0, "failed": 0, "partial": 0, "recovered": 0}, "strict", "completed", EXIT_NO_RESULTS),
        ({"total_files": 0, "failed": 0, "partial": 0, "recovered": 0}, "report-only", "completed", EXIT_OK),
        ({"total_files": 1, "failed": 0, "partial": 0, "recovered": 1}, "strict", "completed", EXIT_OK),
        ({"total_files": 2, "failed": 0, "partial": 1, "recovered": 1}, "strict", "partial", EXIT_PARTIAL),
        ({"total_files": 2, "failed": 0, "partial": 1, "recovered": 1}, "partial-ok", "partial", EXIT_OK),
        ({"total_files": 1, "failed": 1, "partial": 0, "recovered": 0}, "partial-ok", "partial", EXIT_PARTIAL),
        ({"total_files": 1, "failed": 1, "partial": 0, "recovered": 0}, "report-only", "partial", EXIT_OK),
        ({"total_files": 1, "failed": 0, "partial": 0, "recovered": 0}, "report-only", "failed", EXIT_FATAL),
        ({"total_files": 1, "failed": 0, "partial": 0, "recovered": 0}, "report-only", "cancelled", EXIT_FATAL),
    ],
)
def test_exit_policy_matrix(summary, policy, final_state, expected):
    assert _exit_for_summary(summary, policy, final_state) == expected


@pytest.mark.parametrize(
    ("policy", "expected"),
    [("strict", EXIT_PARTIAL), ("partial-ok", EXIT_PARTIAL), ("report-only", EXIT_OK)],
)
def test_unavailable_goal_follows_selected_exit_policy(tmp_path, capsys, monkeypatch, policy, expected):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    input_root.mkdir()
    # Structurally recognizable MP4; normalize deliberately needs disabled tools.
    (input_root / "clip.mp4").write_bytes(
        b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00\x00\x00\x08moov"
    )
    code = main([
        "recover",
        *_common(input_root, tmp_path / "run.sqlite3", tmp_path / "workspace"),
        str(tmp_path / "output"),
        "--goal",
        "normalize",
        "--exit-policy",
        policy,
    ])
    summary = json.loads(capsys.readouterr().out)

    assert code == expected
    assert summary["by_status"] == {"unavailable": 1}
