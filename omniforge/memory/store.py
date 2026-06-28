"""Local SQLite fix-memory. Three tables: incidents, patches, fix_memory.
Phase 0: schema init only. Lookup/remember land in Phase 4.
"""
import sqlite3

from omniforge.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id                  TEXT PRIMARY KEY,
    ts                  TEXT NOT NULL,
    error_type          TEXT NOT NULL,
    traceback           TEXT NOT NULL,
    signature_hash      TEXT NOT NULL,
    source_file         TEXT,
    failing_function    TEXT,
    source_snapshot     TEXT,
    trigger_input       TEXT,
    dependency_versions TEXT,
    log_tail            TEXT,
    status              TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS patches (
    id             TEXT PRIMARY KEY,
    incident_id    TEXT NOT NULL,
    root_cause     TEXT,
    unified_diff   TEXT,
    repro_test     TEXT,
    scan_result    TEXT,
    sandbox_result TEXT,
    deployed       INTEGER NOT NULL DEFAULT 0,
    rollback_of    TEXT,
    model_used     TEXT,
    latency_ms     INTEGER,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS fix_memory (
    signature_hash TEXT PRIMARY KEY,
    patch_id       TEXT NOT NULL,
    hit_count      INTEGER NOT NULL DEFAULT 0,
    last_used      TEXT,
    FOREIGN KEY (patch_id) REFERENCES patches(id)
);

CREATE INDEX IF NOT EXISTS idx_incidents_sig ON incidents(signature_hash);
"""


def connect(db_path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None) -> str:
    """Create the SQLite file + schema if absent. Idempotent."""
    path = db_path or settings.DB_PATH
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return path


if __name__ == "__main__":
    p = init_db()
    print(f"SQLite initialized: {p}")
