"""Opt-in six-turn live Astra cost pilot; consumes cloud usage.

Same installed binary, prompts, schema and settings in all arms. Uses ordinary
Codex authentication. No API credentials are read or copied by this script.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from laya_codex_companion.config import home

CASES = [
    ("arithmetic", "Compute 17 * 23. Return the decimal integer as result.", "391"),
    ("python-aliasing", "Trace this Python without executing it: def f(x, acc=[]): acc.append(x); return acc. "
     "Then a=f(1); b=f(9, []); c=f(2). What are a,b,c now? "
     "Return result as three comma-separated digit strings joined by |, with no spaces (e.g. 3,4|5|6).",
     "1,2|9|1,2"),
]


def estimate(usage):
    """Standard <=272k API-equivalent estimate, not subscription billing."""
    total, cached, writes, output = (usage.get(k, 0) for k in
        ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens"))
    if any(type(n) is not int or n < 0 for n in (total, cached, writes, output)) or cached + writes > total:
        raise ValueError("Invalid token accounting")
    if total > 272000:
        raise ValueError("Pilot exceeds standard short-context pricing scope")
    # Reasoning output is already included in output_tokens. Never add it twice.
    return round(((total - cached - writes) * 10 + cached + writes * 12.5 + output * 50) / 1e6, 6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = home() / "native"
    receipt = json.loads((root / "build.json").read_text(encoding="utf-8"))
    binary = root / receipt["package"] / "bin" / ("codex.exe" if os.name == "nt" else "codex")
    with binary.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "binary_sha256": digest,
              "scope": "Two synthetic single-turn tasks; one sample per arm. Not general coding quality or subscription savings.",
              "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-astra",
              "pricing_date": "2026-09-22", "rates_per_million": {"input": 10, "cached": 1, "write": 12.5, "output": 50},
              "runs": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="laya-cost-") as tmp:
        work = Path(tmp)
        schema = work / "schema.json"
        schema.write_text(json.dumps({"type": "object", "properties": {"result": {"type": "string"}},
                                      "required": ["result"], "additionalProperties": False}), encoding="utf-8")
        for index, (name, task, expected) in enumerate(CASES):
            # Rotate order to reduce a systematic first-arm cache advantage.
            arms = ["low", "medium", "adaptive"]
            arms = arms[index:] + arms[:index]
            for arm in arms:
                logdir = work / (name + "-" + arm)
                env = {**os.environ, "LAYA_CONTROLLER_PYTHON": sys.executable,
                       "LAYA_CONTROLLER_LOG_DIR": str(logdir)}
                command = [str(binary), "--enable", "step_model_switching", "--enable", "reasoning_effort_override",
                           "exec", "--ignore-user-config", "--ephemeral", "--json", "--skip-git-repo-check",
                           "-s", "read-only", "-C", str(work), "-m", "laya-astra" if arm == "adaptive" else "gpt-6-astra",
                           "-c", 'model_reasoning_effort="' + ("medium" if arm == "adaptive" else arm) + '"',
                           "--output-schema", str(schema), "-"]
                print(f"Running {name}: {arm}", flush=True)
                start = time.perf_counter()
                row = {"case": name, "arm": arm, "expected": expected, "prompt": task}
                try:
                    proc = subprocess.run(command, input="Without tools or explanations. " + task,
                                          env=env, capture_output=True, text=True, encoding="utf-8", timeout=240)
                    events = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
                    items = [e["item"] for e in events if e.get("type") == "item.completed"]
                    answers = [i["text"] for i in items if i["type"] == "agent_message"]
                    usage = next(e["usage"] for e in reversed(events) if e.get("type") == "turn.completed")
                    decisions = [json.loads(line) for p in logdir.glob("*.jsonl") for line in p.read_text(encoding="utf-8").splitlines()]
                    tools_used = [i["type"] for i in items if i["type"] not in ("agent_message", "reasoning", "error")]
                    result = json.loads(answers[-1])
                    row.update(returncode=proc.returncode, usage=usage, answer=result, correct=result == {"result": expected},
                               tools_used=tools_used, decisions=decisions, api_equivalent_usd=estimate(usage),
                               valid=proc.returncode == 0 and not tools_used and
                               (bool(decisions) and all(d["applied"] and d["decision"]["status"] == "decided" for d in decisions)
                                if arm == "adaptive" else not decisions))
                except (subprocess.TimeoutExpired, ValueError, StopIteration, KeyError, IndexError) as exc:
                    row.update(valid=False, correct=False, error=type(exc).__name__)
                row["elapsed_seconds"] = round(time.perf_counter() - start, 3)
                report["runs"].append(row)
                save()
    report["summary"] = {arm: {"correct": sum(r["correct"] for r in report["runs"] if r["arm"] == arm),
                               "valid": all(r["valid"] for r in report["runs"] if r["arm"] == arm),
                               "api_equivalent_usd": round(sum(r.get("api_equivalent_usd", 0) for r in report["runs"] if r["arm"] == arm), 6),
                               "elapsed_seconds": round(sum(r["elapsed_seconds"] for r in report["runs"] if r["arm"] == arm), 3)}
                         for arm in ("low", "medium", "adaptive")}
    save()
    print(json.dumps(report["summary"], indent=2))
    return 0 if all(r["valid"] and r["correct"] for r in report["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
