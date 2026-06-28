"""Local SQLite fix-memory. Three tables: incidents, patches, fix_memory.

Phase 0: schema init. Phase 4: remember (persist a validated fix) + lookup
(exact signature-hash match -> skip the model). Repeat errors cost ~0ms/$0 and
hit_count ticks up — the continual-learning payoff.
"""
import datetime
import json
import sqlite3

from omniforge.config import settings
from omniforge.models.schemas import IncidentContext, Patch

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


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save_incident(conn: sqlite3.Connection, ctx: IncidentContext) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO incidents
           (id, ts, error_type, traceback, signature_hash, source_file,
            failing_function, source_snapshot, trigger_input,
            dependency_versions, log_tail, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ctx.id, ctx.ts, ctx.error_type, ctx.traceback, ctx.signature_hash,
         ctx.source_file, ctx.failing_function, ctx.source_snapshot,
         json.dumps(ctx.trigger_input), json.dumps(ctx.dependency_versions),
         json.dumps(ctx.log_tail), ctx.status),
    )
    conn.commit()


def save_patch(conn: sqlite3.Connection, patch: Patch) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO patches
           (id, incident_id, root_cause, unified_diff, repro_test, scan_result,
            sandbox_result, deployed, rollback_of, model_used, latency_ms)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (patch.id, patch.incident_id, patch.root_cause, patch.unified_diff,
         patch.repro_test, json.dumps(patch.scan_result),
         json.dumps(patch.sandbox_result), int(patch.deployed),
         patch.rollback_of, patch.model_used, patch.latency_ms),
    )
    conn.commit()


def remember(conn: sqlite3.Connection, ctx: IncidentContext, patch: Patch) -> None:
    """Persist a validated, deployed fix and key it by error signature so the
    next occurrence is fixed from memory with no model call. hit_count starts 0.
    """
    save_incident(conn, ctx)
    save_patch(conn, patch)
    conn.execute(
        """INSERT OR REPLACE INTO fix_memory
           (signature_hash, patch_id, hit_count, last_used)
           VALUES (?, ?, COALESCE(
               (SELECT hit_count FROM fix_memory WHERE signature_hash = ?), 0),
               ?)""",
        (ctx.signature_hash, patch.id, ctx.signature_hash, _now()),
    )
    conn.commit()


def _row_to_patch(row: sqlite3.Row) -> Patch:
    return Patch(
        id=row["id"], incident_id=row["incident_id"], root_cause=row["root_cause"],
        unified_diff=row["unified_diff"], repro_test=row["repro_test"],
        scan_result=json.loads(row["scan_result"] or "{}"),
        sandbox_result=json.loads(row["sandbox_result"] or "{}"),
        deployed=bool(row["deployed"]), rollback_of=row["rollback_of"],
        model_used=row["model_used"], latency_ms=row["latency_ms"],
    )


def lookup(conn: sqlite3.Connection, ctx: IncidentContext) -> Patch | None:
    """Exact signature-hash match. On a hit: bump hit_count + last_used and
    return the stored Patch (caller skips the model). Miss -> None.
    """
    mem = conn.execute(
        "SELECT patch_id FROM fix_memory WHERE signature_hash = ?",
        (ctx.signature_hash,),
    ).fetchone()
    if mem is None:
        return None
    conn.execute(
        """UPDATE fix_memory SET hit_count = hit_count + 1, last_used = ?
           WHERE signature_hash = ?""",
        (_now(), ctx.signature_hash),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM patches WHERE id = ?", (mem["patch_id"],)
    ).fetchone()
    return _row_to_patch(row) if row else None


def hit_count(conn: sqlite3.Connection, signature_hash: str) -> int:
    row = conn.execute(
        "SELECT hit_count FROM fix_memory WHERE signature_hash = ?",
        (signature_hash,),
    ).fetchone()
    return row["hit_count"] if row else 0


if __name__ == "__main__":
    p = init_db()
    print(f"SQLite initialized: {p}")
