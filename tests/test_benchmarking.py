from __future__ import annotations

import json
import time

import pytest

from file_uncorrupter.benchmarking import ProcessMemorySampler, load_ground_truth
from file_uncorrupter.cli import EXIT_OK, main


def test_process_memory_sampler_records_actual_main_process_rss():
    sampler = ProcessMemorySampler(interval_seconds=0.005)
    sampler.start()
    retained = bytearray(2 * (1 << 20))
    time.sleep(0.02)
    evidence = sampler.stop()

    assert retained
    assert evidence["scope"] == "main_process_recovery_phase"
    assert evidence["children_included"] is False
    assert evidence["sample_count"] >= 2
    assert evidence["baseline_memory_bytes"] > 0
    assert evidence["peak_memory_bytes"] >= evidence["baseline_memory_bytes"]
    assert evidence["peak_over_baseline_bytes"] >= 0
    assert evidence["error"] is None


def test_ground_truth_loader_rejects_unsafe_paths_and_unknown_grades(tmp_path):
    ground_truth = tmp_path / "truth.json"
    ground_truth.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "files": {
                    "../outside.txt": {
                        "recoverable": True,
                        "acceptable_grades": ["invented_grade"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_ground_truth(ground_truth)


def test_benchmark_persists_memory_false_positive_and_per_group_metrics(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    workspace_root = tmp_path / "workspace"
    input_root.mkdir()
    (input_root / "recoverable.txt").write_text("recoverable text\n", encoding="utf-8")
    (input_root / "negative.txt").write_text("the benchmark labels this as unrecoverable\n", encoding="utf-8")
    ground_truth = tmp_path / "ground-truth.json"
    ground_truth.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_name": "synthetic-text-truth",
                "files": {
                    "recoverable.txt": {
                        "family": "text",
                        "recoverable": True,
                        "acceptable_grades": ["validated_original"],
                    },
                    "negative.txt": {
                        "family": "text",
                        "recoverable": False,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "benchmark.sqlite3"
    manifest = tmp_path / "benchmark.json"

    result = main(
        [
            "benchmark",
            str(input_root),
            str(output_root),
            "--db",
            str(database),
            "--workspace-root",
            str(workspace_root),
            "--manifest",
            str(manifest),
            "--ground-truth",
            str(ground_truth),
            "--goal",
            "repair",
            "--all-files",
            "--workers",
            "1",
            "--quiet",
        ]
    )
    capsys.readouterr()

    assert result == EXIT_OK
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    metrics = payload["benchmark"]
    assert metrics["performance"]["peak_memory_bytes"] > 0
    assert metrics["performance"]["memory_measurement"]["method"]
    assert metrics["recovery"]["false_positive_rate"] == 1.0
    assert metrics["recovery"]["false_negative_rate"] == 0.0
    assert metrics["recovery"]["classification_accuracy"] == 1.0
    assert metrics["recovery"]["ground_truth_recovery_accuracy"] == 0.5
    assert metrics["ground_truth"]["groups"]["text"]["fidelity_accuracy"] == 1.0

    regenerated = tmp_path / "regenerated.json"
    assert main(["report", "--db", str(database), "--run-id", "1", "--output-json", str(regenerated)]) == EXIT_OK
    capsys.readouterr()
    regenerated_payload = json.loads(regenerated.read_text(encoding="utf-8"))
    assert regenerated_payload["benchmark"] == metrics
