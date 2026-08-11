import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone

from gateway.agent import Agent, GrokClient
from gateway.config import get_settings
from gateway.db import init_db, get_conn
from gateway.device import DeviceRegistry
from gateway.memory import Memory
from gateway.tools import ToolRegistry
from evals.cases import CASES
from evals.mock_grok import MockGrokClient


def _git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _score(case: dict, calls: list[dict]) -> tuple[float, dict]:
    names = [c["name"] for c in calls]
    required = case.get("required", [])
    forbidden = case.get("forbidden", [])
    arg_checks = case.get("arg_checks", [])

    required_ok = all(r in names for r in required) if required else True
    forbidden_ok = not any(f in names for f in forbidden)
    args_ok = True
    for chk in arg_checks:
        match = [c for c in calls if c["name"] == chk["tool"]]
        args_ok = args_ok and bool(match) and \
            match[0]["args"].get(chk["arg"]) == chk["equals"]

    score = (0.5 if required_ok else 0.0) + (0.3 if forbidden_ok else 0.0) \
        + (0.2 if args_ok else 0.0)
    return score, {"required_ok": required_ok, "forbidden_ok": forbidden_ok,
                   "args_ok": args_ok, "called": names}


async def _run_case(case: dict, agent: Agent) -> dict:
    repeat = case.get("repeat", 1)
    all_calls = []
    for _ in range(repeat):
        out = await agent.run_cycle(dict(case["context"]))
        all_calls.extend(out["tool_calls"])
    score, detail = _score(case, all_calls)
    return {"case_id": case["id"], "score": score, "passed": score >= 0.8,
            "detail": detail}


def run_evals(db_path: str, mode: str = "mock",
              case_ids: list | None = None,
              results_dir: str = "evals/results") -> dict:
    init_db(db_path)
    memory = Memory(db_path)
    registry = DeviceRegistry(memory)
    tools = ToolRegistry(registry)
    if mode == "live":
        client = GrokClient(get_settings())
    else:
        client = MockGrokClient()
    agent = Agent(memory, tools, client)

    cases = [c for c in CASES if not case_ids or c["id"] in case_ids]
    results = [asyncio.run(_run_case(c, agent)) for c in cases]

    passed = sum(1 for r in results if r["passed"])
    summary = {"total": len(results), "passed": passed,
               "failed": len(results) - passed,
               "average_score": round(
                   sum(r["score"] for r in results) / max(1, len(results)), 2)}
    # Microsecond resolution: two runs within the same second must not
    # collide on the eval_runs.run_id UNIQUE constraint.
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    record = {"run_id": run_id,
              "metadata": {"mode": mode, "git_sha": _git_sha()},
              "summary": summary, "results": results}

    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, f"run_{run_id}.json"), "w") as f:
        json.dump(record, f, indent=2)

    conn = get_conn(db_path)
    try:
        conn.execute("INSERT INTO eval_runs (run_id, ts, mode, model, git_sha,"
                     " summary_json) VALUES (?,?,?,?,?,?)",
                     (run_id, datetime.now(timezone.utc).isoformat(), mode,
                      getattr(client, "model", "mock"), _git_sha(),
                      json.dumps(summary)))
        for r in results:
            conn.execute("INSERT INTO eval_results (run_id, case_id, passed,"
                         " score, detail_json) VALUES (?,?,?,?,?)",
                         (run_id, r["case_id"], int(r["passed"]), r["score"],
                          json.dumps(r["detail"])))
        # diff vs previous run
        rows = conn.execute(
            "SELECT run_id, summary_json FROM eval_runs ORDER BY id DESC"
            " LIMIT 2").fetchall()
        conn.commit()
    finally:
        conn.close()

    comparison = {"baseline": False, "previous_run_id": None}
    if len(rows) == 2:
        prev_summary = json.loads(rows[1]["summary_json"])
        comparison = {
            "baseline": True,
            "previous_run_id": rows[1]["run_id"],
            "score_delta": round(
                summary["average_score"] - prev_summary["average_score"], 2),
        }
    record["comparison"] = comparison
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--db", default="gateway/guardian.db")
    parser.add_argument("--cases", nargs="*", default=None)
    args = parser.parse_args()
    out = run_evals(db_path=args.db, mode=args.mode, case_ids=args.cases)
    s = out["summary"]
    print(f"run {out['run_id']}: {s['passed']}/{s['total']} passed "
          f"(avg {s['average_score']})")


if __name__ == "__main__":
    main()
