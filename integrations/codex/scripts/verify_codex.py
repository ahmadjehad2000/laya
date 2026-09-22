"""Exercise the installed plugin in a fresh authenticated Codex CLI session."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
output = root / "dist" / "codex-smoke.jsonl"
output.parent.mkdir(parents=True, exist_ok=True)
prompt = """This is a read-only acceptance test of the installed Laya for Codex plugin.
Use its laya_status tool, then laya_predict_batch for these two independent records:
id en: 'I was charged twice. Please refund the duplicate charge.'
id ar: 'تم خصم المبلغ مرتين، أرجو إعادة المبلغ الزائد.'
Ask one choice question for department using billing=payments/refunds,
technical=software failures, sales=new purchases. Use model multilingual.
Report actual returned labels and runtime backend/device. Check labels against the given
source sentences. Then call laya_release. Do not use shell or web tools and do not edit files.
If plugin tools are unavailable, say so; do not simulate tool results."""
command = [shutil.which("codex") or "codex", "exec", "--ephemeral", "--sandbox", "read-only",
           "--json", "-"]
with output.open("w", encoding="utf-8") as stream:
    result = subprocess.run(command, input=prompt, cwd=root, stdout=stream, stderr=subprocess.PIPE, text=True, encoding="utf-8")
calls = []
for line in output.read_text(encoding="utf-8").splitlines():
    event = json.loads(line)
    item = event.get("item", {})
    if event.get("type") == "item.completed" and item.get("type") == "mcp_tool_call" and item.get("server") == "laya-for-codex":
        calls.append(item)
successful = {c["tool"] for c in calls if c.get("status") == "completed" and not c.get("error")}
passed = result.returncode == 0 and {"laya_status", "laya_predict_batch", "laya_release"} <= successful
report = {"passed": passed, "scope": "Actual fresh Codex CLI session, completed plugin tool calls only", "calls": calls}
evidence = root / "integrations/codex/evidence/codex-native.json"
evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"passed": passed, "exit_code": result.returncode, "transcript": str(output),
                  "evidence": str(evidence), "stderr": result.stderr[-1500:]}, indent=2))
sys.exit(0 if passed else 1)
