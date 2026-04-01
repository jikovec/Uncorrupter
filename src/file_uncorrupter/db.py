from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .types import Candidate, Classification, DecodeResult, FileRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    input_root TEXT,
    output_root TEXT,
    engine_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    declared_kind TEXT,
    byte0_kind TEXT NOT NULL,
    classification_family TEXT,
    classification_label TEXT,
    classification_confidence REAL,
    evidence_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    strategy_id TEXT NOT NULL,
    family TEXT NOT NULL,
    priority INTEGER NOT NULL,
    decoder TEXT NOT NULL,
    ok INTEGER NOT NULL,
    width INTEGER,
    height INTEGER,
    mode TEXT,
    decoded_format TEXT,
    score REAL,
    error TEXT,
    meta_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id)
);

CREATE TABLE IF NOT EXISTS outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    strategy_id TEXT,
    decoder TEXT,
    output_path TEXT,
    raw_candidate_path TEXT,
    width INTEGER,
    height INTEGER,
    score REAL,
    success INTEGER NOT NULL,
    error TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id)
);
"""


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def start_run(conn: sqlite3.Connection, command: str, input_root: Path | None, output_root: Path | None, engine_name: str | None) -> int:
    cursor = conn.execute(
        "INSERT INTO runs (command, input_root, output_root, engine_name) VALUES (?, ?, ?, ?)",
        (
            command,
            str(input_root) if input_root else None,
            str(output_root) if output_root else None,
            engine_name,
        ),
    )
    return int(cursor.lastrowid)


def insert_file(conn: sqlite3.Connection, run_id: int, record: FileRecord, classification: Classification | None) -> int:
    cursor = conn.execute(
        """
        INSERT INTO files (
            run_id, relative_path, absolute_path, size, sha256, declared_kind, byte0_kind,
            classification_family, classification_label, classification_confidence, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            str(record.relative_path),
            str(record.path),
            record.size,
            record.sha256,
            record.declared_kind,
            record.byte0_kind,
            classification.family if classification else None,
            classification.label if classification else None,
            classification.confidence if classification else None,
            json.dumps(classification.evidence, ensure_ascii=False) if classification else None,
        ),
    )
    return int(cursor.lastrowid)


def insert_attempt(conn: sqlite3.Connection, run_id: int, file_id: int, candidate: Candidate, decode: DecodeResult) -> None:
    conn.execute(
        """
        INSERT INTO attempts (
            run_id, file_id, strategy_id, family, priority, decoder, ok, width, height, mode,
            decoded_format, score, error, meta_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            file_id,
            candidate.strategy_id,
            candidate.family,
            candidate.priority,
            decode.decoder,
            1 if decode.ok else 0,
            decode.width,
            decode.height,
            decode.mode,
            decode.decoded_format,
            decode.score,
            decode.error,
            json.dumps(candidate.meta, ensure_ascii=False),
        ),
    )


def insert_output(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    candidate: Candidate | None,
    decode: DecodeResult,
    raw_candidate_path: Path | None,
) -> None:
    conn.execute(
        """
        INSERT INTO outputs (
            run_id, file_id, strategy_id, decoder, output_path, raw_candidate_path, width, height,
            score, success, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            file_id,
            candidate.strategy_id if candidate else None,
            decode.decoder,
            str(decode.output_path) if decode.output_path else None,
            str(raw_candidate_path) if raw_candidate_path else None,
            decode.width,
            decode.height,
            decode.score,
            1 if decode.ok else 0,
            decode.error,
        ),
    )


def latest_run_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return int(row["id"])


def fetch_summary(conn: sqlite3.Connection, run_id: int) -> dict:
    summary: dict[str, object] = {}
    run_row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if run_row is None:
        raise ValueError(f"Run {run_id} not found")

    total = conn.execute("SELECT COUNT(*) AS c FROM files WHERE run_id = ?", (run_id,)).fetchone()["c"]
    success = conn.execute("SELECT COUNT(*) AS c FROM outputs WHERE run_id = ? AND success = 1", (run_id,)).fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) AS c FROM outputs WHERE run_id = ? AND success = 0", (run_id,)).fetchone()["c"]

    def aggregate(query: str) -> dict[str, int]:
        rows = conn.execute(query, (run_id,)).fetchall()
        return {str(row[0]) if row[0] is not None else "none": int(row[1]) for row in rows}

    summary.update(
        {
            "run_id": run_id,
            "command": run_row["command"],
            "input_root": run_row["input_root"],
            "output_root": run_row["output_root"],
            "engine_name": run_row["engine_name"],
            "created_at": run_row["created_at"],
            "total_files": int(total),
            "recovered": int(success),
            "failed": int(failed),
            "by_classification": aggregate(
                "SELECT classification_label, COUNT(*) FROM files WHERE run_id = ? GROUP BY classification_label ORDER BY COUNT(*) DESC, classification_label"
            ),
            "by_decoder": aggregate(
                "SELECT decoder, COUNT(*) FROM outputs WHERE run_id = ? GROUP BY decoder ORDER BY COUNT(*) DESC, decoder"
            ),
            "by_strategy": aggregate(
                "SELECT strategy_id, COUNT(*) FROM outputs WHERE run_id = ? GROUP BY strategy_id ORDER BY COUNT(*) DESC, strategy_id"
            ),
            "top_errors": aggregate(
                "SELECT error, COUNT(*) FROM outputs WHERE run_id = ? AND success = 0 GROUP BY error ORDER BY COUNT(*) DESC, error"
            ),
        }
    )
    return summary


def fetch_attempt_rows(conn: sqlite3.Connection, run_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT f.relative_path, a.strategy_id, a.family, a.priority, a.decoder, a.ok, a.width, a.height,
               a.mode, a.decoded_format, a.score, a.error
        FROM attempts a
        JOIN files f ON f.id = a.file_id
        WHERE a.run_id = ?
        ORDER BY a.file_id, a.id
        """,
        (run_id,),
    ).fetchall()
