import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    trigger TEXT NOT NULL,
    temp_c REAL, humidity_pct REAL, light INTEGER, motion INTEGER,
    raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    trigger TEXT NOT NULL,
    source TEXT NOT NULL,
    context_json TEXT NOT NULL,
    tool_calls_json TEXT NOT NULL,
    latency_ms REAL, input_tokens INTEGER, output_tokens INTEGER
);
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmd_id TEXT UNIQUE NOT NULL,
    device_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    action TEXT NOT NULL,
    args_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    ack_ts TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    ts TEXT NOT NULL, mode TEXT NOT NULL,
    model TEXT, git_sha TEXT, summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eval_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL, case_id TEXT NOT NULL,
    passed INTEGER NOT NULL, score REAL NOT NULL, detail_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status);
"""


def init_db(path: str) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
