"""Check the real installed worker with the native child's restricted environment."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    allowed = {"PATH", "USERNAME", "USER", "LOGNAME", "COMSPEC", "SYSTEMDRIVE", "HOMEDRIVE", "HOMEPATH", "PROGRAMDATA",
               "PATHEXT", "SYSTEMROOT", "WINDIR", "APPDATA", "LOCALAPPDATA",
               "USERPROFILE", "HOME", "TEMP", "TMP", "TMPDIR", "LD_LIBRARY_PATH",
               "DYLD_LIBRARY_PATH", "HF_HOME", "HF_HUB_CACHE", "TORCH_HOME"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed or
           k.upper().startswith(("LAYA_COMPANION_", "CUDA_"))}
    request = {"protocol": 1, "id": "worker:1", "generation": 1, "model": "gpt-6-astra",
               "supported_efforts": ["low", "medium", "high", "xhigh", "max"],
               "evidence": {"requests": ["Inspect a failing test; do not deploy. Report unresolved failures."], "recent": []}}
    requests = [request, {**request, "id": "worker:2", "generation": 2}]
    completed = subprocess.run([sys.executable, "-I", "-m", "laya_codex_companion.controller"],
                               input="".join(json.dumps(r) + "\n" for r in requests), env=env,
                               capture_output=True, text=True, encoding="utf-8", timeout=180,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        replies = [json.loads(line) for line in completed.stdout.splitlines()]
    except ValueError:
        replies = []
    passed = completed.returncode == 0 and len(replies) == 2 and all(r["status"] == "decided" for r in replies)
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "passed": passed,
              "returncode": completed.returncode, "responses": replies}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not passed:
        print(completed.stderr[:3000] + "\n" + completed.stderr[-6000:], file=sys.stderr)
        print(repr(completed.stdout[-1000:]), file=sys.stderr)
    print(json.dumps(report))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
