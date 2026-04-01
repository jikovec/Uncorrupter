from __future__ import annotations

import csv
import json
from pathlib import Path

from .db import fetch_attempt_rows, fetch_summary


def write_json_report(conn, run_id: int, output_path: Path) -> dict:
    summary = fetch_summary(conn, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def write_attempts_csv(conn, run_id: int, output_path: Path) -> None:
    rows = fetch_attempt_rows(conn, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "relative_path",
            "strategy_id",
            "family",
            "priority",
            "decoder",
            "ok",
            "width",
            "height",
            "mode",
            "decoded_format",
            "score",
            "error",
        ])
        for row in rows:
            writer.writerow([
                row["relative_path"],
                row["strategy_id"],
                row["family"],
                row["priority"],
                row["decoder"],
                row["ok"],
                row["width"],
                row["height"],
                row["mode"],
                row["decoded_format"],
                row["score"],
                row["error"],
            ])
