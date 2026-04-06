from file_uncorrupter.classification import classify_record
from file_uncorrupter.db import connect, fetch_summary, start_run
from file_uncorrupter.intake import build_file_record


def test_run_summary_counts_files(tmp_path):
    db_path = tmp_path / "runs.sqlite3"
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"\xff\xd8abc\xff\xd9")
    data = image_path.read_bytes()
    record = build_file_record(tmp_path, image_path, data)
    classification = classify_record(record, data)

    from file_uncorrupter.db import insert_file

    with connect(db_path) as conn:
        run_id = start_run(conn, "scan", tmp_path, None, "baseline-v2", workspace_root=tmp_path / ".uncorrupter-workspace", config={})
        insert_file(conn, run_id, record, classification)
        summary = fetch_summary(conn, run_id)

    assert summary["total_files"] == 1
    assert summary["recovered"] == 0
    assert summary["by_anywhere_kind"]["jpeg"] == 1
