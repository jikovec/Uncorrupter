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



def test_insert_candidate_returns_real_candidate_id_on_duplicate(tmp_path):
    db_path = tmp_path / "runs.sqlite3"
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"\xff\xd8abc\xff\xd9")
    data = image_path.read_bytes()
    record = build_file_record(tmp_path, image_path, data)
    classification = classify_record(record, data)

    from file_uncorrupter.db import insert_candidate, insert_file, insert_attempt
    from file_uncorrupter.types import Candidate, DecodeResult

    with connect(db_path) as conn:
        run_id = start_run(conn, "recover", tmp_path, tmp_path / "out", "baseline-v2", workspace_root=tmp_path / ".uncorrupter-workspace", config={})
        file_id = insert_file(conn, run_id, record, classification)

        candidate = Candidate(
            strategy_id="jpeg_test_duplicate",
            family="jpeg",
            priority=10,
            data=data,
            provenance=[{"kind": "slice", "start": 0, "end": len(data)}],
        )

        first_candidate_id = insert_candidate(conn, run_id, file_id, candidate)
        insert_attempt(conn, run_id, file_id, first_candidate_id, DecodeResult(ok=True, decoder="pillow"), phase="probe")

        second_candidate_id = insert_candidate(conn, run_id, file_id, candidate)
        insert_attempt(conn, run_id, file_id, second_candidate_id, DecodeResult(ok=True, decoder="pillow"), phase="probe_duplicate")

        assert second_candidate_id == first_candidate_id


def test_summary_counts_successful_image_outputs(tmp_path):
    db_path = tmp_path / "runs.sqlite3"
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"\xff\xd8abc\xff\xd9")
    data = image_path.read_bytes()
    record = build_file_record(tmp_path, image_path, data)
    classification = classify_record(record, data)

    from file_uncorrupter.db import insert_attempt, insert_file, insert_output
    from file_uncorrupter.types import Artifact, DecodeResult

    out_path = tmp_path / "out.jpg"
    out_path.write_bytes(b"jpg")
    with connect(db_path) as conn:
        run_id = start_run(conn, "recover", tmp_path, tmp_path / "out", "baseline-v2", workspace_root=tmp_path / ".uncorrupter-workspace", config={})
        file_id = insert_file(conn, run_id, record, classification)
        attempt_id = insert_attempt(conn, run_id, file_id, None, DecodeResult(ok=True, decoder="pillow", width=10, height=10), phase="image_final")
        insert_output(
            conn,
            run_id,
            file_id,
            attempt_id,
            None,
            DecodeResult(ok=True, decoder="pillow", width=10, height=10, output_path=out_path),
            Artifact(artifact_type="image", path=out_path, sha256="abc", decoder="pillow", width=10, height=10),
            None,
        )
        summary = fetch_summary(conn, run_id)

    assert summary["recovered"] == 1
    assert summary["by_output_type"]["image"] == 1
