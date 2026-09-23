"""Inspect, or explicitly enable and trust, the installed Laya prompt gate."""
import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="Persist trust after reviewing the local hook")
    args = parser.parse_args()
    binary = shutil.which("codex")
    if not binary:
        raise SystemExit("Codex CLI is required")
    process = subprocess.Popen([binary, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    replies = queue.Queue()

    def read_replies():
        for line in process.stdout:
            replies.put(line)
        replies.put(None)

    reader = threading.Thread(target=read_replies, daemon=True)
    reader.start()

    def rpc(identity, method, params):
        process.stdin.write(json.dumps({"id": identity, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        while True:
            line = replies.get(timeout=60)
            if line is None:
                raise RuntimeError("Codex app-server exited")
            response = json.loads(line)
            if response.get("id") == identity:
                if "error" in response:
                    raise RuntimeError(response["error"])
                return response["result"]

    try:
        rpc(1, "initialize", {"clientInfo": {"name": "laya-setup", "version": "0.3.0"},
                              "capabilities": {"experimentalApi": True}})
        process.stdin.write('{"method":"initialized"}\n')
        process.stdin.flush()
        result = rpc(2, "hooks/list", {"cwds": [str(Path.cwd())]})
        hooks = [hook for item in result["data"] for hook in item["hooks"]
                 if (hook.get("pluginId") or "").startswith("laya-for-codex@")]
        print(json.dumps(hooks, indent=2))
        if args.enable and not hooks:
            raise RuntimeError("Laya hook is not installed; run bootstrap.py register first")
        for identity, hook in enumerate(hooks if args.enable else [], 10):
            if hook["eventName"] != "userPromptSubmit" or hook["handlerType"] != "command":
                raise RuntimeError("Unexpected Laya hook; inspect it before enabling")
            rpc(identity, "config/value/write", {
                "keyPath": "hooks.state." + json.dumps(hook["key"]),
                "value": {"enabled": True, "trusted_hash": hook["currentHash"]},
                "mergeStrategy": "replace"})
        if args.enable:
            print("Laya prompt hook enabled and trusted. Start a new Codex thread.")
    finally:
        process.stdin.close()
        process.terminate()
        process.wait(timeout=10)
        reader.join(timeout=5)


if __name__ == "__main__":
    main()
