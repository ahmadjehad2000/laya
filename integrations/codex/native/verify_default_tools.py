"""Live acceptance: ordinary task, no user mention of Laya and no plugin config."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from laya_codex_companion.config import home


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="laya-default-") as tmp:
        root = Path(tmp)
        records = [{"id": "outage", "state": "The payment API returns HTTP 503. Incident PAY-42. Retry queue is stopped."}]
        records += [{"id": f"other-{i}", "state": "The football club won the final championship."} for i in range(20)]
        (root / "records.json").write_text(json.dumps(records), encoding="utf-8")
        prompt = ("Find relevant evidence about the payment API outage in records.json. "
                  "Use a bounded context selection workflow rather than loading the complete collection. "
                  "Report the incident ID, symptom and queue state with source record IDs. "
                  "Save the evidence-selection report locally. Do not edit the source or use the network.")
        completed = subprocess.run([sys.executable, "-I", "-m", "laya_codex_companion", "exec",
            "--ignore-user-config", "--ephemeral", "--json", "--skip-git-repo-check", "-s", "read-only",
            "-C", str(root), "-"], input=prompt, text=True, encoding="utf-8", capture_output=True, timeout=240)
        events = [json.loads(line) for line in completed.stdout.splitlines() if line.startswith("{")]
        items = [e["item"] for e in events if e.get("type") == "item.completed"]
        calls = [i for i in items if i.get("type") == "mcp_tool_call"]
        answer = "\n".join(i["text"] for i in items if i.get("type") == "agent_message")
        thread = next((e["thread_id"] for e in events if e.get("type") == "thread.started"), None)
        log = home() / "native/logs" / (str(thread) + ".jsonl")
        audit = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        artifacts = [json.loads(p.read_text(encoding="utf-8")) for p in (root / ".laya/results").glob("*.json")]
        checks = {"exit_success": completed.returncode == 0,
                  "default_context_tool": any(i.get("tool") == "laya_context_file" and i.get("status") == "completed" and not i.get("error") for i in calls),
                  "source_retained": all(s in answer for s in ("PAY-42", "503", "outage")),
                  "artifact_written": bool(artifacts),
                  "controller_applied": any(d.get("applied") and d["decision"]["status"] == "decided" for d in audit)}
        report = {"timestamp": datetime.now(timezone.utc).isoformat(), "checks": checks,
                  "prompt": prompt, "answer": answer, "calls": calls, "decisions": audit,
                  "usage": [e.get("usage") for e in events if e.get("type") == "turn.completed"],
                  "scope": "One live no-plugin-config context-selection task; tool choice remains model-dependent"}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(checks))
        if not all(checks.values()):
            print(completed.stderr[-3000:])
        return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
