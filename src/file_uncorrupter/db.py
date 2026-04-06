from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .types import Artifact, Candidate, Classification, DecodeResult, FileRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    input_root TEXT,
    output_root TEXT,
    workspace_root TEXT,
    engine_name TEXT,
    config_json TEXT,
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
    anywhere_kind TEXT,
    signature_summary_json TEXT,
    classification_family TEXT,
    classification_label TEXT,
    classification_confidence REAL,
    evidence_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    family TEXT NOT NULL,
    signature_type TEXT NOT NULL,
    offset INTEGER NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id)
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    strategy_id TEXT NOT NULL,
    family TEXT NOT NULL,
    candidate_kind TEXT NOT NULL,
    priority INTEGER NOT NULL,
    dedupe_hash TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    provenance_json TEXT,
    meta_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    UNIQUE(run_id, file_id, dedupe_hash)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    candidate_id INTEGER,
    decoder TEXT NOT NULL,
    phase TEXT NOT NULL,
    ok INTEGER NOT NULL,
    width INTEGER,
    height INTEGER,
    mode TEXT,
    decoded_format TEXT,
    duration_ms INTEGER,
    frame_count INTEGER,
    score REAL,
    error TEXT,
    telemetry_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);

CREATE TABLE IF NOT EXISTS outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    attempt_id INTEGER,
    strategy_id TEXT,
    decoder TEXT,
    output_type TEXT,
    output_path TEXT,
    artifact_sha256 TEXT,
    raw_candidate_path TEXT,
    width INTEGER,
    height INTEGER,
    duration_ms INTEGER,
    frame_count INTEGER,
    score REAL,
    success INTEGER NOT NULL,
    error TEXT,
    meta_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(attempt_id) REFERENCES attempts(id)
);

CREATE TABLE IF NOT EXISTS frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output_id INTEGER NOT NULL,
    pts_ms INTEGER,
    is_keyframe INTEGER NOT NULL DEFAULT 0,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    meta_json TEXT,
    FOREIGN KEY(output_id) REFERENCES outputs(id)
);
"""


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def start_run(
    conn: sqlite3.Connection,
    command: str,
    input_root: Path | None,
    output_root: Path | None,
    engine_name: str | None,
    *,
    workspace_root: Path | None = None,
    config: dict | None = None,
) -> int:
    cursor = conn.execute(
        "INSERT INTO runs (command, input_root, output_root, workspace_root, engine_name, config_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            command,
            str(input_root) if input_root else None,
            str(output_root) if output_root else None,
            str(workspace_root) if workspace_root else None,
            engine_name,
            json.dumps(config or {}, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def insert_file(conn: sqlite3.Connection, run_id: int, record: FileRecord, classification: Classification | None) -> int:
    cursor = conn.execute(
        """
        INSERT INTO files (
            run_id, relative_path, absolute_path, size, sha256, declared_kind, byte0_kind,
            anywhere_kind, signature_summary_json, classification_family, classification_label,
            classification_confidence, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            str(record.relative_path),
            str(record.path),
            record.size,
            record.sha256,
            record.declared_kind,
            record.byte0_kind,
            record.anywhere_kind,
            json.dumps(record.signature_summary, ensure_ascii=False),
            classification.family if classification else None,
            classification.label if classification else None,
            classification.confidence if classification else None,
            json.dumps(classification.evidence, ensure_ascii=False) if classification else None,
        ),
    )
    file_id = int(cursor.lastrowid)
    for hit in record.signature_hits:
        conn.execute(
            "INSERT INTO signatures (run_id, file_id, family, signature_type, offset, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, file_id, hit.family, hit.signature_type, hit.offset, hit.confidence),
        )
    return file_id


def insert_candidate(conn: sqlite3.Connection, run_id: int, file_id: int, candidate: Candidate) -> int:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO candidates (
            run_id, file_id, strategy_id, family, candidate_kind, priority, dedupe_hash,
            payload_sha256, provenance_json, meta_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            file_id,
            candidate.strategy_id,
            candidate.family,
            candidate.candidate_kind,
            candidate.priority,
            candidate.dedupe_hash,
            candidate.data_sha256,
            json.dumps(candidate.provenance, ensure_ascii=False),
            json.dumps(candidate.meta, ensure_ascii=False),
        ),
    )
    if cursor.lastrowid:
        return int(cursor.lastrowid)
    row = conn.execute(
        "SELECT id FROM candidates WHERE run_id = ? AND file_id = ? AND dedupe_hash = ?",
        (run_id, file_id, candidate.dedupe_hash),
    ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_persist_candidate")
    return int(row["id"])


def insert_attempt(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    candidate_id: int | None,
    decode: DecodeResult,
    *,
    phase: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO attempts (
            run_id, file_id, candidate_id, decoder, phase, ok, width, height, mode,
            decoded_format, duration_ms, frame_count, score, error, telemetry_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            file_id,
            candidate_id,
            decode.decoder,
            phase,
            1 if decode.ok else 0,
            decode.width,
            decode.height,
            decode.mode,
            decode.decoded_format,
            decode.duration_ms,
            decode.frame_count,
            decode.score,
            decode.error,
            json.dumps(decode.telemetry, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def insert_output(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    attempt_id: int | None,
    candidate: Candidate | None,
    decode: DecodeResult,
    artifact: Artifact | None,
    raw_candidate_path: Path | None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO outputs (
            run_id, file_id, attempt_id, strategy_id, decoder, output_type, output_path,
            artifact_sha256, raw_candidate_path, width, height, duration_ms, frame_count,
            score, success, error, meta_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            file_id,
            attempt_id,
            candidate.strategy_id if candidate else None,
            decode.decoder,
            artifact.artifact_type if artifact else None,
            str(artifact.path) if artifact else (str(decode.output_path) if decode.output_path else None),
            artifact.sha256 if artifact else None,
            str(raw_candidate_path) if raw_candidate_path else None,
            artifact.width if artifact else decode.width,
            artifact.height if artifact else decode.height,
            artifact.duration_ms if artifact else decode.duration_ms,
            artifact.frame_count if artifact else decode.frame_count,
            decode.score,
            1 if decode.ok else 0,
            decode.error,
            json.dumps(artifact.meta if artifact else decode.telemetry, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


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
    success = conn.execute(
        "SELECT COUNT(DISTINCT file_id) AS c FROM outputs WHERE run_id = ? AND success = 1",
        (run_id,),
    ).fetchone()["c"]
    failed = max(0, int(total) - int(success))

    def aggregate(query: str) -> dict[str, int]:
        rows = conn.execute(query, (run_id,)).fetchall()
        return {str(row[0]) if row[0] is not None else "none": int(row[1]) for row in rows}

    summary.update(
        {
            "run_id": run_id,
            "command": run_row["command"],
            "input_root": run_row["input_root"],
            "output_root": run_row["output_root"],
            "workspace_root": run_row["workspace_root"],
            "engine_name": run_row["engine_name"],
            "created_at": run_row["created_at"],
            "total_files": int(total),
            "recovered": int(success),
            "failed": int(failed),
            "by_classification": aggregate(
                "SELECT classification_label, COUNT(*) FROM files WHERE run_id = ? GROUP BY classification_label ORDER BY COUNT(*) DESC, classification_label"
            ),
            "by_family": aggregate(
                "SELECT classification_family, COUNT(*) FROM files WHERE run_id = ? GROUP BY classification_family ORDER BY COUNT(*) DESC, classification_family"
            ),
            "by_anywhere_kind": aggregate(
                "SELECT anywhere_kind, COUNT(*) FROM files WHERE run_id = ? GROUP BY anywhere_kind ORDER BY COUNT(*) DESC, anywhere_kind"
            ),
            "by_decoder": aggregate(
                "SELECT decoder, COUNT(*) FROM outputs WHERE run_id = ? AND success = 1 GROUP BY decoder ORDER BY COUNT(*) DESC, decoder"
            ),
            "by_strategy": aggregate(
                "SELECT strategy_id, COUNT(*) FROM outputs WHERE run_id = ? AND success = 1 GROUP BY strategy_id ORDER BY COUNT(*) DESC, strategy_id"
            ),
            "by_output_type": aggregate(
                "SELECT output_type, COUNT(*) FROM outputs WHERE run_id = ? AND success = 1 GROUP BY output_type ORDER BY COUNT(*) DESC, output_type"
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
        SELECT f.relative_path, c.strategy_id, c.family, c.priority, a.phase, a.decoder, a.ok, a.width, a.height,
               a.mode, a.decoded_format, a.duration_ms, a.frame_count, a.score, a.error
        FROM attempts a
        JOIN files f ON f.id = a.file_id
        LEFT JOIN candidates c ON c.id = a.candidate_id
        WHERE a.run_id = ?
        ORDER BY a.file_id, a.id
        """,
        (run_id,),
    ).fetchall()
