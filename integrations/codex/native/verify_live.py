"""Explicit paid/usage-consuming live Astra handoff acceptance; no benchmark claim."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from laya_codex_companion.compaction import compact_file
from laya_codex_companion.config import home

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    native_root = home() / "native"
    build = json.loads((native_root / "build.json").read_text(encoding="utf-8"))
    binary = native_root / build["package"] / "bin" / ("codex.exe" if sys.platform == "win32" else "codex")
    with binary.open("rb") as stream:
        binary_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    handoff = compact_file(ROOT, "integrations/codex/examples/tutorial/conversation.json", keep_recent=2)
    command = [sys.executable, "-I", "-m", "laya_codex_companion", "continue", "--workspace", str(ROOT),
               "--context", handoff["context"], "--target", "laya-codex", "--lean", "--model", "laya-astra",
               "--prompt", "Without tools, list the retained demonstration branch, memory budget, deployment restriction, "
               "and unresolved status. State whether the export proves that any real tests ran. Be concise."]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=240)
    events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip().startswith("{")]
    thread_id = next((event["thread_id"] for event in events if event["type"] == "thread.started"), None)
    items = [event["item"] for event in events if event["type"] == "item.completed"]
    answer = "\n".join(item["text"] for item in items if item["type"] == "agent_message")
    used_tools = [item["type"] for item in items if item["type"] not in ("agent_message", "error", "reasoning")]
    audit = []
    if thread_id:
        log = home() / "native/logs" / (thread_id + ".jsonl")
        if log.is_file():
            audit = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    checks = {"exit_success": completed.returncode == 0,
              "turn_completed": any(event["type"] == "turn.completed" for event in events),
              "no_tools": not used_tools,
              "branch_retained": "feat/tutorial" in answer,
              "budget_retained": "250" in answer and "MiB" in answer,
              "deployment_mentioned": "deploy" in answer.lower(),
              "unresolved_retained": "unresolved" in answer.lower(),
              "native_capture_audited": bool(audit) and all(record["applied"] for record in audit)}
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "real_openai_generations": True,
              "binary_sha256": binary_sha256, "source_commit": build["commit"],
              "patch_sha256": build["patch_sha256"],
              "fixture": "explicit-fictional-tutorial-handoff", "checks": checks, "answer": answer,
              "usage": [event.get("usage") for event in events if event["type"] == "turn.completed"],
              "decisions": audit, "tool_types": used_tools,
              "scope": "One recall acceptance case, not a coding-quality or cost-savings benchmark"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not all(checks.values()):
        print(completed.stderr[-3000:], file=sys.stderr)
        print(completed.stdout[-3000:], file=sys.stderr)
    print(json.dumps({"checks": checks, "answer": answer}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
