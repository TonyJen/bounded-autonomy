import json
from datetime import datetime, timedelta, timezone
from gateway.db import get_conn

# Seconds a queued/pushed command stays valid. Minted into every command
# envelope (device.py, app.py) and enforced here, at the chokepoint the
# firmware's net.h assigns expiry to: "the gateway's queue owns expiry".
COMMAND_TTL_S = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def insert_snapshot(self, device_id: str, type: str, trigger: str,
                        sensors: dict, raw: dict) -> int:
        conn = get_conn(self.db_path)
        try:
            cur = conn.execute(
                "INSERT INTO snapshots (device_id, ts, type, trigger, temp_c,"
                " humidity_pct, light, motion, raw_json)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (device_id, _now(), type, trigger,
                 sensors.get("temp_c"), sensors.get("humidity_pct"),
                 sensors.get("light"), int(bool(sensors.get("motion"))),
                 json.dumps(raw)))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def recent_snapshots(self, limit: int = 10) -> list[dict]:
        conn = get_conn(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM snapshots ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def latest_snapshot(self) -> dict | None:
        rows = self.recent_snapshots(1)
        return rows[0] if rows else None

    def record_decision(self, trigger: str, source: str, context: dict,
                        tool_calls: list, latency_ms: float, usage: dict) -> int:
        conn = get_conn(self.db_path)
        try:
            cur = conn.execute(
                "INSERT INTO decisions (ts, trigger, source, context_json,"
                " tool_calls_json, latency_ms, input_tokens, output_tokens)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (_now(), trigger, source, json.dumps(context),
                 json.dumps(tool_calls), latency_ms,
                 usage.get("prompt_tokens"), usage.get("completion_tokens")))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def recent_decisions(self, limit: int = 10) -> list[dict]:
        conn = get_conn(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def queue_command(self, device_id: str, action: str, args: dict,
                      cmd_id: str) -> None:
        conn = get_conn(self.db_path)
        try:
            conn.execute(
                "INSERT INTO commands (cmd_id, device_id, ts, action, args_json)"
                " VALUES (?,?,?,?,?)",
                (cmd_id, device_id, _now(), action, json.dumps(args)))
            conn.commit()
        finally:
            conn.close()

    def commands_after(self, device_id: str, after_id: int) -> list[dict]:
        # Enforce the advertised ttl_s before serving: anything older is
        # marked 'expired' and never reaches the device. 'pushed' commands
        # past the TTL expire too — the device either already executed them
        # (ack lost) or never will, and re-serving either way is wrong.
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(seconds=COMMAND_TTL_S)).isoformat()
        conn = get_conn(self.db_path)
        try:
            conn.execute(
                "UPDATE commands SET status='expired' WHERE device_id=?"
                " AND status IN ('queued','pushed') AND ts < ?",
                (device_id, cutoff))
            conn.commit()
            rows = conn.execute(
                "SELECT * FROM commands WHERE device_id=? AND id>?"
                " AND status IN ('queued','pushed') ORDER BY id",
                (device_id, after_id)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def set_command_status(self, cmd_id: str, status: str,
                           error: str | None = None) -> None:
        conn = get_conn(self.db_path)
        try:
            conn.execute(
                "UPDATE commands SET status=?, ack_ts=?, error=? WHERE cmd_id=?",
                (status, _now() if status == "acked" else None, error, cmd_id))
            conn.commit()
        finally:
            conn.close()

    def mark_pushed(self, cmd_id: str) -> None:
        """queued → pushed only. The device acks immediately on push now, so
        the ack can land before the gateway records the push — 'pushed' must
        never clobber 'acked'."""
        conn = get_conn(self.db_path)
        try:
            conn.execute(
                "UPDATE commands SET status='pushed' WHERE cmd_id=?"
                " AND status='queued'", (cmd_id,))
            conn.commit()
        finally:
            conn.close()

    def get_command(self, cmd_id: str) -> dict | None:
        conn = get_conn(self.db_path)
        try:
            row = conn.execute(
                "SELECT action, args_json, status FROM commands"
                " WHERE cmd_id=?",
                (cmd_id,)).fetchone()
            if row is None:
                return None
            return {"action": row["action"], "status": row["status"],
                    "args": json.loads(row["args_json"])}
        finally:
            conn.close()

    def prune_old_snapshots(self, days: int = 7) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = get_conn(self.db_path)
        try:
            conn.execute("DELETE FROM snapshots WHERE ts < ?", (cutoff,))
            conn.commit()
        finally:
            conn.close()
