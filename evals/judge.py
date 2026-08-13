"""LLM-as-judge for free-text outputs (log_observation notes, OLED
display_text lines) — the only open-ended generation in the system.

Per OpenAI eval best practices: pass/fail verdicts over numeric scores, a
clear detailed rubric, reasoning before the verdict, and calibration against
human labels (`python -m evals.judge --calibrate`) before judge scores are
trusted. Judge results are REPORTED in run summaries, not gated.

Runs in live mode only; mock mode skips the judge to stay deterministic.
"""

import argparse
import asyncio
import json
import os
import re
import sys

JUDGE_SYSTEM_PROMPT = (
    "You are a strict evaluator for a room-monitoring device called Grok "
    "Guardian. The device reads sensors (temperature °C, humidity %, light "
    "0-4095, motion) and takes physical actions via tools (set_fan, "
    "set_servo, set_led, buzzer, display_text, log_observation). You grade "
    "the device's FREE-TEXT outputs: log_observation notes and display_text "
    "OLED lines.\n"
    "Rubric — an output PASSES only if ALL hold:\n"
    "1. Grounded: every sensor value it mentions matches the actual "
    "context; no fabricated readings.\n"
    "2. Consistent: actions it describes were actually taken; it does not "
    "claim actions that did not happen or contradict ones that did.\n"
    "3. Appropriate: factual, calm, no alarms without cause, no mention of "
    "nonexistent capabilities (e.g. heater, camera).\n"
    "4. Informative: not empty or content-free.\n"
    "Length limits (note <= 280 chars, OLED line <= 16 chars) are enforced "
    "elsewhere — do not grade length.\n"
    "Think step by step about each criterion, then respond with ONLY a JSON "
    "object: {\"passed\": true|false, \"reason\": \"one sentence\"}."
)

_VERDICT_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_verdict(content: str) -> dict:
    """Extract {\"passed\": bool, \"reason\": str} from judge output."""
    for match in _VERDICT_RE.finditer(content or ""):
        try:
            obj = json.loads(match.group(0))
        except ValueError:
            continue
        if isinstance(obj.get("passed"), bool):
            return {"pass": obj["passed"],
                    "reason": str(obj.get("reason", ""))[:200]}
    return {"pass": False,
            "reason": f"judge_error: unparseable verdict: {(content or '')[:120]}"}


class Judge:
    """Grades free-text outputs against context using a Grok-compatible
    client. Inject any object with an async chat(messages, tools) method."""

    def __init__(self, client):
        self.client = client

    async def judge(self, contexts: list[dict], actions: list[str],
                    outputs: list[dict]) -> dict:
        """contexts: the sensor snapshots from the case; actions: tool names
        called; outputs: [{"tool": ..., "args": {...}}] free-text calls.
        Fails soft: a judge outage yields a judge_error verdict rather than
        killing the eval run (judge scores are reported, not gated)."""
        user = json.dumps({
            "contexts": contexts,
            "actions_taken": actions,
            "free_text_outputs": outputs,
        })
        try:
            resp = await self.client.chat(
                [{"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                 {"role": "user", "content": user}],
                None)
            message = resp["choices"][0]["message"]
        except Exception as e:
            return {"pass": False,
                    "reason": f"judge_error: {type(e).__name__}: {e}"[:200]}
        return _parse_verdict(message.get("content") or "")


def _calibration_path() -> str:
    return os.path.join(os.path.dirname(__file__),
                        "calibration", "judge_labels.json")


async def _calibrate(judge: Judge, path: str) -> tuple[float, list[dict]]:
    with open(path) as f:
        examples = json.load(f)
    mismatches = []
    for ex in examples:
        verdict = await judge.judge(ex["contexts"], ex["actions_taken"],
                                    ex["free_text_outputs"])
        if verdict["pass"] != ex["label"]:
            mismatches.append({"id": ex["id"], "label": ex["label"],
                               "judge": verdict["pass"],
                               "reason": verdict["reason"]})
    agreement = (len(examples) - len(mismatches)) / max(1, len(examples))
    return agreement, mismatches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", action="store_true",
                        help="run the judge against the human-labeled "
                             "calibration set and report agreement")
    parser.add_argument("--threshold", type=float, default=0.85)
    args = parser.parse_args()

    if args.calibrate:
        from gateway.agent import GrokClient
        from gateway.config import get_settings
        judge = Judge(GrokClient(get_settings()))
        agreement, mismatches = asyncio.run(
            _calibrate(judge, _calibration_path()))
        print(f"judge/human agreement: {agreement:.0%} "
              f"(threshold {args.threshold:.0%})")
        for m in mismatches:
            print(f"  MISMATCH {m['id']}: human={m['label']} "
                  f"judge={m['judge']} — {m['reason']}")
        sys.exit(0 if agreement >= args.threshold else 1)


if __name__ == "__main__":
    main()
