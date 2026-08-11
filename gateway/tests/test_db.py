import os
import sqlite3
from gateway.db import init_db, get_conn


def test_init_db_creates_tables(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    conn = get_conn(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "decisions", "commands", "eval_runs", "eval_results"} <= tables
    conn.close()


def test_get_conn_row_factory(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    conn = get_conn(db)
    conn.execute("INSERT INTO snapshots (device_id, ts, type, trigger, raw_json) "
                 "VALUES ('d1', '2026-01-01T00:00:00Z', 'heartbeat', 'periodic', '{}')")
    row = conn.execute("SELECT * FROM snapshots").fetchone()
    assert row["device_id"] == "d1"  # dict-style access
    conn.close()
