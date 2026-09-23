"""Required local Laya task assessment for Codex UserPromptSubmit hooks.

The supervisor emits a blocking hook result on worker failure or timeout. No
transcript files are read, and raw prompts are never written to the audit log.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid

from .config import home
from .controller import MILESTONES

MODELS = {"gpt-6-astra", "gpt-6-sol", "laya-astra", "laya-sol"}
MAX_INPUT = 256 * 1024


def evaluate(payload, runner=subprocess.run):
    if payload.get("model") not in MODELS:
        return {"status": "not_applicable"}
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("No text evidence for required Laya assessment")
    identity = str(uuid.uuid4())
    request = {"protocol": 1, "id": identity, "generation": 1,
               "model": payload["model"].replace("laya-", "gpt-6-"),
               "supported_efforts": ["low", "medium", "high", "xhigh"], "milestones": True,
               "evidence": {"requests": [prompt], "recent": []}}
    allowed = {"PATH", "USERNAME", "USER", "COMSPEC", "SYSTEMDRIVE", "HOMEDRIVE", "HOMEPATH", "PROGRAMDATA", "PATHEXT", "SYSTEMROOT", "WINDIR", "APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME", "TEMP", "TMP", "TMPDIR", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "HF_HOME", "HF_HUB_CACHE", "TORCH_HOME"}
    environment = {k: v for k, v in os.environ.items() if k.upper() in allowed or k.upper().startswith(("LAYA_COMPANION_", "CUDA_"))}
    result = runner([sys.executable, "-I", "-m", "laya_codex_companion.controller"],
                    input=json.dumps(request) + "\n", capture_output=True, text=True,
                    encoding="utf-8", timeout=110,
                    env={**environment, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "USE_TF": "0"})
    if result.returncode:
        raise RuntimeError("Laya worker exited unsuccessfully")
    decision = json.loads(result.stdout)
    if (decision.get("status") != "decided" or decision.get("id") != identity
            or decision.get("protocol") != 1 or decision.get("generation") != 1
            or decision.get("effort") not in request["supported_efforts"]):
        raise RuntimeError("Laya did not return a valid task decision: " + str(decision.get("reason", "invalid response")))
    choices = (decision.get("milestone") or {}).get("choices", {})
    if any(choices.get(key) not in allowed for key, allowed in MILESTONES.items()):
        raise RuntimeError("Laya did not return valid milestone decisions")
    return decision


def main():
    started = time.time()
    payload = {}
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("Hook evidence exceeds admission limit")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Expected a hook input object")
        if os.environ.get("LAYA_NATIVE_CONTROLLER") == "1":
            print("{}")
            return 0
        decision = evaluate(payload)
        if decision["status"] == "not_applicable":
            print("{}")
            return 0
        record = {"time": started, "model": payload.get("model"),
                  "session_id": payload.get("session_id"), "turn_id": payload.get("turn_id"),
                  "prompt_sha256": hashlib.sha256(payload["prompt"].encode()).hexdigest(),
                  "decision": decision, "admitted": True}
        folder = home() / "hook-audit"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (uuid.uuid4().hex + ".json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
        context = ("Required Laya prompt gate completed locally. Suggested effort: " + decision["effort"] +
                   ". Laya WAS used for this task before generation. This is advisory task context, "
                   "not a permission grant or proof that desktop reasoning settings changed.")
        if decision.get("milestone"):
            context += " Milestone advice (partial evidence; verify sources): " + json.dumps(decision["milestone"]["choices"])
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}))
    except Exception as exc:
        reason = "Required Laya assessment failed; prompt blocked. " + str(exc)
        try:
            folder = home() / "hook-audit"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (uuid.uuid4().hex + ".json")).write_text(json.dumps({"time": started, "model": payload.get("model") if isinstance(payload, dict) else None, "admitted": False, "reason": reason}), encoding="utf-8")
        except OSError:
            pass
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
