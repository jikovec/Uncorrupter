from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator

from .types import Artifact, Candidate, Classification, DecodeResult, FileRecord

CURRENT_SCHEMA_VERSION = 2


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return {"kind": "bytes", "length": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, set):
        return sorted(value, key=str)
    raise TypeError(f"unsupported evidence value: {value.__class__.__name__}")


def _json_dumps(value, *, sort_keys: bool = False) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=sort_keys, default=_json_default)

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

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    strategy_hash TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    priority INTEGER NOT NULL,
    provenance_json TEXT,
    meta_json TEXT,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id),
    UNIQUE(candidate_id, strategy_hash)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    UNIQUE(run_id, sequence)
);

CREATE TABLE IF NOT EXISTS budget_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER,
    attempt_id INTEGER,
    scope TEXT NOT NULL,
    budget_name TEXT NOT NULL,
    limit_value REAL NOT NULL,
    consumed REAL NOT NULL,
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(attempt_id) REFERENCES attempts(id)
);

CREATE TABLE IF NOT EXISTS artifact_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    child_output_id INTEGER,
    relation_type TEXT NOT NULL,
    parent_kind TEXT NOT NULL,
    parent_identifier TEXT NOT NULL,
    locator_json TEXT NOT NULL,
    transform_json TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(child_output_id) REFERENCES outputs(id)
);

CREATE TABLE IF NOT EXISTS text_spans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output_id INTEGER NOT NULL,
    source_start INTEGER NOT NULL,
    source_end INTEGER NOT NULL,
    output_start INTEGER NOT NULL,
    output_end INTEGER NOT NULL,
    encoding TEXT NOT NULL,
    span_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    diagnostic TEXT,
    FOREIGN KEY(output_id) REFERENCES outputs(id)
);

CREATE TABLE IF NOT EXISTS archive_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    safe_name TEXT,
    header_offset INTEGER,
    method TEXT,
    compressed_size INTEGER,
    uncompressed_size INTEGER,
    checksum TEXT,
    flags_json TEXT NOT NULL,
    outcome TEXT NOT NULL,
    output_id INTEGER,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(output_id) REFERENCES outputs(id)
);

CREATE TABLE IF NOT EXISTS document_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    locator TEXT NOT NULL,
    media_type TEXT,
    flags_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    output_id INTEGER,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(output_id) REFERENCES outputs(id)
);

CREATE TABLE IF NOT EXISTS media_streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    stream_index INTEGER NOT NULL,
    stream_type TEXT,
    codec TEXT,
    evidence_json TEXT NOT NULL,
    output_id INTEGER,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(output_id) REFERENCES outputs(id)
);

CREATE TABLE IF NOT EXISTS tool_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_id INTEGER,
    attempt_id INTEGER,
    name TEXT NOT NULL,
    resolved_path TEXT,
    version TEXT,
    available INTEGER NOT NULL,
    policy_id TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(attempt_id) REFERENCES attempts(id)
);

"""

INDEX_SCHEMA = """

CREATE INDEX IF NOT EXISTS idx_files_run_id ON files(run_id);
CREATE INDEX IF NOT EXISTS idx_files_classification_label ON files(classification_label);
CREATE INDEX IF NOT EXISTS idx_signatures_file_id ON signatures(file_id);
CREATE INDEX IF NOT EXISTS idx_candidates_run_file ON candidates(run_id, file_id);
CREATE INDEX IF NOT EXISTS idx_attempts_run_file ON attempts(run_id, file_id);
CREATE INDEX IF NOT EXISTS idx_outputs_run_file ON outputs(run_id, file_id);
CREATE INDEX IF NOT EXISTS idx_frames_output_id ON frames(output_id);
CREATE INDEX IF NOT EXISTS idx_events_run_sequence ON events(run_id, sequence);
CREATE INDEX IF NOT EXISTS idx_budget_events_run_file ON budget_events(run_id, file_id);
CREATE INDEX IF NOT EXISTS idx_artifact_relations_child ON artifact_relations(child_output_id);
"""


def _column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    if column_name not in _column_names(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def _ensure_schema_upgrades(conn: sqlite3.Connection) -> None:
    # Older shipped databases may predate these columns. CREATE TABLE IF NOT EXISTS
    # will not retrofit them, so we migrate in place.
    for name, definition in (
        ("input_root", "TEXT"),
        ("output_root", "TEXT"),
        ("workspace_root", "TEXT"),
        ("engine_name", "TEXT"),
        ("config_json", "TEXT"),
        ("state", "TEXT NOT NULL DEFAULT 'created'"),
        ("database_path", "TEXT"),
        ("goals_json", "TEXT"),
        ("application_version", "TEXT"),
        ("platform_json", "TEXT"),
        ("tools_json", "TEXT"),
        ("started_at", "TEXT"),
        ("finished_at", "TEXT"),
        ("resume_of_run_id", "INTEGER"),
        ("cancellation_reason", "TEXT"),
        ("fatal_error", "TEXT"),
    ):
        _add_column_if_missing(conn, "runs", name, definition)

    _add_column_if_missing(conn, "files", "anywhere_kind", "TEXT")
    _add_column_if_missing(conn, "files", "signature_summary_json", "TEXT")
    _add_column_if_missing(conn, "files", "classification_family", "TEXT")
    _add_column_if_missing(conn, "files", "classification_label", "TEXT")
    _add_column_if_missing(conn, "files", "classification_confidence", "REAL")
    _add_column_if_missing(conn, "files", "evidence_json", "TEXT")
    _add_column_if_missing(conn, "files", "modified_ns", "INTEGER")
    _add_column_if_missing(conn, "files", "device_id", "INTEGER")
    _add_column_if_missing(conn, "files", "inode_id", "INTEGER")
    _add_column_if_missing(conn, "files", "status", "TEXT NOT NULL DEFAULT 'discovered'")
    _add_column_if_missing(conn, "files", "started_at", "TEXT")
    _add_column_if_missing(conn, "files", "finished_at", "TEXT")
    _add_column_if_missing(conn, "files", "error_code", "TEXT")
    _add_column_if_missing(conn, "files", "error_detail", "TEXT")

    _add_column_if_missing(conn, "candidates", "content_hash", "TEXT")
    _add_column_if_missing(conn, "candidates", "estimated_materialized_bytes", "INTEGER")
    _add_column_if_missing(conn, "candidates", "estimated_output_bytes", "INTEGER")

    _add_column_if_missing(conn, "attempts", "duration_ms", "INTEGER")
    _add_column_if_missing(conn, "attempts", "frame_count", "INTEGER")
    _add_column_if_missing(conn, "attempts", "score", "REAL")
    _add_column_if_missing(conn, "attempts", "telemetry_json", "TEXT")
    _add_column_if_missing(conn, "attempts", "outcome_grade", "TEXT")
    _add_column_if_missing(conn, "attempts", "started_at", "TEXT")
    _add_column_if_missing(conn, "attempts", "finished_at", "TEXT")

    _add_column_if_missing(conn, "outputs", "artifact_sha256", "TEXT")
    _add_column_if_missing(conn, "outputs", "raw_candidate_path", "TEXT")
    _add_column_if_missing(conn, "outputs", "duration_ms", "INTEGER")
    _add_column_if_missing(conn, "outputs", "frame_count", "INTEGER")
    _add_column_if_missing(conn, "outputs", "score", "REAL")
    _add_column_if_missing(conn, "outputs", "meta_json", "TEXT")
    _add_column_if_missing(conn, "outputs", "media_type", "TEXT")
    _add_column_if_missing(conn, "outputs", "size", "INTEGER")
    _add_column_if_missing(conn, "outputs", "fidelity_grade", "TEXT")
    _add_column_if_missing(conn, "outputs", "validation_state", "TEXT")
    _add_column_if_missing(conn, "outputs", "validators_json", "TEXT")
    _add_column_if_missing(conn, "outputs", "publication_state", "TEXT")

    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(CURRENT_SCHEMA_VERSION),),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        _ensure_schema_upgrades(conn)
        conn.executescript(INDEX_SCHEMA)
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
    goals: list[str] | None = None,
    application_version: str | None = None,
    platform: dict | None = None,
    tools: dict | None = None,
    resume_of_run_id: int | None = None,
    database_path: Path | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO runs (
            command, input_root, output_root, workspace_root, engine_name, config_json,
            state, database_path, goals_json, application_version, platform_json,
            tools_json, resume_of_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, 'created', ?, ?, ?, ?, ?, ?)
        """,
        (
            command,
            str(input_root) if input_root else None,
            str(output_root) if output_root else None,
            str(workspace_root) if workspace_root else None,
            engine_name,
            _json_dumps(config or {}),
            str(database_path) if database_path else None,
            _json_dumps(goals or []),
            application_version,
            _json_dumps(platform or {}),
            _json_dumps(tools or {}),
            resume_of_run_id,
        ),
    )
    return int(cursor.lastrowid)


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        return 0
    return int(row[0])


_RUN_TRANSITIONS = {
    "created": {"running", "cancelled", "failed"},
    "running": {"completed", "partial", "cancelled", "failed"},
    "completed": set(),
    "partial": set(),
    "cancelled": set(),
    "failed": set(),
}


def transition_run(
    conn: sqlite3.Connection,
    run_id: int,
    state: str,
    *,
    cancellation_reason: str | None = None,
    fatal_error: str | None = None,
) -> None:
    row = conn.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"Run {run_id} not found")
    current = str(row["state"] or "created")
    if current not in _RUN_TRANSITIONS:
        raise ValueError(f"unknown persisted run state: {current}")
    if not _RUN_TRANSITIONS[current]:
        raise ValueError(f"run {run_id} is terminal in state {current}")
    if state not in _RUN_TRANSITIONS[current]:
        raise ValueError(f"invalid run transition: {current} -> {state}")
    now = _utc_now()
    started_at = now if state == "running" else None
    finished_at = now if state in {"completed", "partial", "cancelled", "failed"} else None
    conn.execute(
        """
        UPDATE runs
        SET state = ?, started_at = COALESCE(started_at, ?), finished_at = ?,
            cancellation_reason = COALESCE(?, cancellation_reason), fatal_error = COALESCE(?, fatal_error)
        WHERE id = ?
        """,
        (state, started_at, finished_at, cancellation_reason, fatal_error, run_id),
    )


def insert_file(conn: sqlite3.Connection, run_id: int, record: FileRecord, classification: Classification | None) -> int:
    cursor = conn.execute(
        """
        INSERT INTO files (
            run_id, relative_path, absolute_path, size, sha256, declared_kind, byte0_kind,
            anywhere_kind, signature_summary_json, classification_family, classification_label,
            classification_confidence, evidence_json, modified_ns, device_id, inode_id, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered')
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
            _json_dumps(record.signature_summary),
            classification.family if classification else None,
            classification.label if classification else None,
            classification.confidence if classification else None,
            _json_dumps(classification.evidence) if classification else None,
            record.modified_ns,
            record.device_id,
            record.inode_id,
        ),
    )
    file_id = int(cursor.lastrowid)
    for hit in record.signature_hits:
        conn.execute(
            "INSERT INTO signatures (run_id, file_id, family, signature_type, offset, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, file_id, hit.family, hit.signature_type, hit.offset, hit.confidence),
        )
    if classification is not None:
        conn.execute("UPDATE files SET status = 'classified' WHERE id = ?", (file_id,))
    return file_id


def transition_file(
    conn: sqlite3.Connection,
    file_id: int,
    status: str,
    *,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> None:
    allowed = {
        "discovered", "scanned", "classified", "processing", "recovered", "partial",
        "skipped", "unavailable", "budget_exceeded", "cancelled", "failed",
    }
    if status not in allowed:
        raise ValueError(f"unknown file status: {status}")
    row = conn.execute("SELECT status FROM files WHERE id = ?", (file_id,)).fetchone()
    if row is None:
        raise ValueError(f"File {file_id} not found")
    now = _utc_now()
    conn.execute(
        """
        UPDATE files
        SET status = ?, started_at = CASE WHEN ? = 'processing' THEN COALESCE(started_at, ?) ELSE started_at END,
            finished_at = CASE WHEN ? IN ('recovered','partial','skipped','unavailable','budget_exceeded','cancelled','failed') THEN ? ELSE finished_at END,
            error_code = ?, error_detail = ?
        WHERE id = ?
        """,
        (status, status, now, status, now, error_code, error_detail, file_id),
    )


@contextmanager
def file_transaction(conn: sqlite3.Connection, file_key: int | str) -> Iterator[None]:
    """Bound a single file's evidence writes without rolling back earlier files."""
    token = "file_" + "".join(character if character.isalnum() else "_" for character in str(file_key))
    conn.execute(f"SAVEPOINT {token}")
    try:
        yield
    except Exception:
        conn.execute(f"ROLLBACK TO SAVEPOINT {token}")
        conn.execute(f"RELEASE SAVEPOINT {token}")
        raise
    else:
        conn.execute(f"RELEASE SAVEPOINT {token}")


def insert_candidate(conn: sqlite3.Connection, run_id: int, file_id: int, candidate: Candidate) -> int:
    conn.execute(
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
            _json_dumps(candidate.provenance),
            _json_dumps(candidate.meta),
        ),
    )
    row = conn.execute(
        "SELECT id FROM candidates WHERE run_id = ? AND file_id = ? AND dedupe_hash = ?",
        (run_id, file_id, candidate.dedupe_hash),
    ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_persist_candidate")
    candidate_id = int(row["id"])
    for link in candidate.strategy_links:
        conn.execute(
            """
            INSERT OR IGNORE INTO candidate_strategies (
                candidate_id, strategy_hash, strategy_id, priority, provenance_json, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                link["strategy_hash"],
                link["strategy_id"],
                link["priority"],
                _json_dumps(link.get("provenance", [])),
                _json_dumps(link.get("meta", {})),
            ),
        )
    conn.execute(
        "UPDATE candidates SET content_hash = COALESCE(content_hash, ?) WHERE id = ?",
        (candidate.data_sha256, candidate_id),
    )
    return candidate_id


def insert_event(
    conn: sqlite3.Connection,
    run_id: int,
    event_type: str,
    payload: dict,
    *,
    sequence: int,
    file_id: int | None = None,
) -> int:
    cursor = conn.execute(
        "INSERT INTO events (run_id, file_id, sequence, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, file_id, sequence, event_type, _json_dumps(payload, sort_keys=True), _utc_now()),
    )
    return int(cursor.lastrowid)


def next_event_sequence(conn: sqlite3.Connection, run_id: int) -> int:
    row = conn.execute("SELECT COALESCE(MAX(sequence), 0) + 1 AS sequence FROM events WHERE run_id = ?", (run_id,)).fetchone()
    return int(row["sequence"])


def insert_budget_event(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    name: str,
    limit_value: int | float,
    consumed: int | float,
    outcome: str,
    scope: str = "run",
    file_id: int | None = None,
    attempt_id: int | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO budget_events (
            run_id, file_id, attempt_id, scope, budget_name, limit_value, consumed, outcome, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, file_id, attempt_id, scope, name, limit_value, consumed, outcome, _utc_now()),
    )
    return int(cursor.lastrowid)


def insert_artifact_relation(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    child_output_id: int | None,
    relation_type: str,
    parent_kind: str,
    parent_identifier: str,
    locator: dict | None = None,
    transform: dict | None = None,
) -> int:
    allowed = {
        "derived_from", "extracted_from", "preview_of", "frame_of", "member_of",
        "page_of", "stream_of", "validates", "supersedes",
    }
    if relation_type not in allowed:
        raise ValueError(f"unsupported artifact relation: {relation_type}")
    cursor = conn.execute(
        """
        INSERT INTO artifact_relations (
            run_id, child_output_id, relation_type, parent_kind, parent_identifier, locator_json, transform_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            child_output_id,
            relation_type,
            parent_kind,
            parent_identifier,
            _json_dumps(locator or {}, sort_keys=True),
            _json_dumps(transform or {}, sort_keys=True),
        ),
    )
    return int(cursor.lastrowid)


def insert_text_spans(conn: sqlite3.Connection, output_id: int, spans: list[dict]) -> int:
    inserted = 0
    for span in spans:
        conn.execute(
            """
            INSERT INTO text_spans (
                output_id, source_start, source_end, output_start, output_end,
                encoding, span_type, confidence, diagnostic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                output_id,
                int(span["source_start"]),
                int(span["source_end"]),
                int(span["output_start"]),
                int(span["output_end"]),
                str(span.get("encoding") or "unknown"),
                str(span.get("span_type") or "unknown"),
                float(span.get("confidence") or 0.0),
                str(span["diagnostic"]) if span.get("diagnostic") is not None else None,
            ),
        )
        inserted += 1
    return inserted


def insert_archive_members(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    members: list[dict],
    *,
    output_id: int | None = None,
) -> int:
    inserted = 0
    for member in members:
        known = {
            "name", "original_name", "safe_name", "header_offset", "method",
            "compressed_size", "uncompressed_size", "checksum", "outcome",
        }
        flags = {key: value for key, value in member.items() if key not in known and key != "artifact_path"}
        conn.execute(
            """
            INSERT INTO archive_members (
                run_id, file_id, original_name, safe_name, header_offset, method,
                compressed_size, uncompressed_size, checksum, flags_json, outcome, output_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                file_id,
                str(member.get("original_name") or member.get("name") or ""),
                member.get("safe_name"),
                member.get("header_offset"),
                str(member["method"]) if member.get("method") is not None else None,
                member.get("compressed_size"),
                member.get("uncompressed_size"),
                member.get("checksum"),
                _json_dumps(flags, sort_keys=True),
                str(member.get("outcome") or "unknown"),
                output_id,
            ),
        )
        inserted += 1
    return inserted


def insert_document_parts(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    parts: list[dict],
    *,
    output_id: int | None = None,
) -> int:
    inserted = 0
    for part in parts:
        flags = {
            key: part[key]
            for key in ("required", "parsed", "macro", "active_content")
            if key in part
        }
        warnings = []
        if part.get("warning"):
            warnings.append(part["warning"])
        conn.execute(
            """
            INSERT INTO document_parts (
                run_id, file_id, locator, media_type, flags_json, warnings_json, output_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                file_id,
                str(part.get("name") or part.get("locator") or ""),
                part.get("media_type"),
                _json_dumps(flags, sort_keys=True),
                _json_dumps(warnings, sort_keys=True),
                output_id,
            ),
        )
        inserted += 1
    return inserted


def insert_media_streams(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    streams: list[dict],
    *,
    output_id: int | None = None,
) -> int:
    inserted = 0
    for position, stream in enumerate(streams):
        conn.execute(
            """
            INSERT INTO media_streams (
                run_id, file_id, stream_index, stream_type, codec, evidence_json, output_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                file_id,
                int(stream.get("index", position)),
                stream.get("type") or stream.get("codec_type"),
                stream.get("codec") or stream.get("codec_name"),
                _json_dumps(stream, sort_keys=True),
                output_id,
            ),
        )
        inserted += 1
    return inserted


def insert_tool_record(
    conn: sqlite3.Connection,
    run_id: int,
    name: str,
    evidence: dict,
    *,
    file_id: int | None = None,
    attempt_id: int | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO tool_records (
            run_id, file_id, attempt_id, name, resolved_path, version,
            available, policy_id, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            file_id,
            attempt_id,
            name,
            evidence.get("resolved_path"),
            evidence.get("version"),
            1 if evidence.get("available") else 0,
            str(evidence.get("policy_id") or "bounded-v1"),
            _json_dumps(evidence, sort_keys=True),
        ),
    )
    return int(cursor.lastrowid)


def insert_attempt(
    conn: sqlite3.Connection,
    run_id: int,
    file_id: int,
    candidate_id: int | None,
    decode: DecodeResult,
    *,
    phase: str,
    outcome_grade: str | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO attempts (
            run_id, file_id, candidate_id, decoder, phase, ok, width, height, mode,
            decoded_format, duration_ms, frame_count, score, error, telemetry_json,
            outcome_grade, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            _json_dumps(decode.telemetry),
            outcome_grade,
            _utc_now(),
            _utc_now(),
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
            score, success, error, meta_json, media_type, size, fidelity_grade,
            validation_state, validators_json, publication_state
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            _json_dumps(artifact.meta if artifact else decode.telemetry),
            artifact.media_type if artifact else None,
            artifact.size if artifact else None,
            artifact.fidelity_grade if artifact else None,
            artifact.validation_state if artifact else None,
            _json_dumps(artifact.validators) if artifact else None,
            "published" if artifact and artifact.published else "not_published",
        ),
    )
    return int(cursor.lastrowid)


def latest_run_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return int(row["id"])


def fetch_run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"Run {run_id} not found")
    return row


def fetch_resume_files(conn: sqlite3.Connection, run_id: int) -> dict[str, sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT id, relative_path, size, sha256, modified_ns, device_id, inode_id, status,
               error_code, error_detail
        FROM files
        WHERE run_id = ?
        ORDER BY relative_path, id
        """,
        (run_id,),
    ).fetchall()
    return {str(row["relative_path"]): row for row in rows}


def source_identity_matches(row: sqlite3.Row, record: FileRecord) -> bool:
    return (
        int(row["size"]) == record.size
        and str(row["sha256"]) == record.sha256
        and int(row["modified_ns"] or 0) == record.modified_ns
        and int(row["device_id"] or 0) == record.device_id
        and int(row["inode_id"] or 0) == record.inode_id
    )


def fetch_manifest_rows(conn: sqlite3.Connection, run_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT f.id AS file_id, f.relative_path, f.size, f.sha256 AS source_sha256,
               f.classification_family, f.classification_label,
               f.classification_confidence, f.status, f.error_code, f.error_detail,
               o.id AS output_id, o.output_type, o.output_path, o.artifact_sha256,
               o.media_type, o.size AS output_size, o.fidelity_grade,
               o.validation_state, o.publication_state, o.success, o.error,
               a.outcome_grade, a.decoder, a.phase
        FROM files f
        LEFT JOIN outputs o ON o.file_id = f.id AND o.run_id = f.run_id
        LEFT JOIN attempts a ON a.id = o.attempt_id
        WHERE f.run_id = ?
        ORDER BY f.relative_path COLLATE NOCASE, f.id, o.output_path COLLATE NOCASE, o.id
        """,
        (run_id,),
    ).fetchall()


def fetch_summary(conn: sqlite3.Connection, run_id: int) -> dict:
    summary: dict[str, object] = {}
    run_row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if run_row is None:
        raise ValueError(f"Run {run_id} not found")

    total = conn.execute("SELECT COUNT(*) AS c FROM files WHERE run_id = ?", (run_id,)).fetchone()["c"]
    success = conn.execute(
        """
        SELECT COUNT(DISTINCT f.id) AS c
        FROM files f
        LEFT JOIN outputs o ON o.file_id = f.id AND o.run_id = f.run_id AND o.success = 1
        WHERE f.run_id = ? AND (f.status = 'recovered' OR o.id IS NOT NULL)
        """,
        (run_id,),
    ).fetchone()["c"]
    partial = conn.execute(
        "SELECT COUNT(*) AS c FROM files WHERE run_id = ? AND status = 'partial'",
        (run_id,),
    ).fetchone()["c"]
    failed = conn.execute(
        """
        SELECT COUNT(*) AS c FROM files
        WHERE run_id = ? AND status IN ('failed','unavailable','budget_exceeded','cancelled')
        """,
        (run_id,),
    ).fetchone()["c"]

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
            "state": run_row["state"],
            "created_at": run_row["created_at"],
            "started_at": run_row["started_at"],
            "finished_at": run_row["finished_at"],
            "resume_of_run_id": run_row["resume_of_run_id"],
            "total_files": int(total),
            "recovered": int(success),
            "partial": int(partial),
            "failed": int(failed),
            "by_status": aggregate(
                "SELECT status, COUNT(*) FROM files WHERE run_id = ? GROUP BY status ORDER BY status"
            ),
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
            "by_outcome_grade": aggregate(
                "SELECT outcome_grade, COUNT(*) FROM attempts WHERE run_id = ? GROUP BY outcome_grade ORDER BY COUNT(*) DESC, outcome_grade"
            ),
            "budget_stops": aggregate(
                "SELECT budget_name, COUNT(*) FROM budget_events WHERE run_id = ? AND outcome = 'exceeded' GROUP BY budget_name ORDER BY budget_name"
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
        SELECT f.relative_path, f.status AS file_status, c.strategy_id, c.family, c.priority,
               a.phase, a.decoder, a.ok, a.width, a.height, a.mode, a.decoded_format,
               a.duration_ms, a.frame_count, a.score, a.error, a.outcome_grade
        FROM attempts a
        JOIN files f ON f.id = a.file_id
        LEFT JOIN candidates c ON c.id = a.candidate_id
        WHERE a.run_id = ?
        ORDER BY a.file_id, a.id
        """,
        (run_id,),
    ).fetchall()
