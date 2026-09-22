"""Exercise the installed native CLI against a local Responses fixture.

No OpenAI calls, authentication or repository changes. Laya inference is real by
default; --missing-worker separately verifies explicit native fallback.
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time


def sse(event):
    return "event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--missing-worker", action="store_true")
    parser.add_argument("--unified", action="store_true", help="Exercise installed laya-for-codex dispatch and its default model")
    args = parser.parse_args()
    if args.unified and args.missing_worker:
        parser.error("Use the direct binary for missing-worker injection")
    if args.unified:
        from laya_codex_companion.config import home
        native_root = home() / "native"
        receipt = json.loads((native_root / "build.json").read_text(encoding="utf-8"))
        installed = native_root / receipt["package"] / "bin" / ("codex.exe" if os.name == "nt" else "codex")
        if installed.resolve() != args.binary.resolve():
            parser.error("--binary must match the unified launcher's installed receipt")
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            index = len(requests)
            if index < 3:
                item = {"type": "function_call", "id": f"fc-{index}", "call_id": f"call-{index}",
                        "name": "nonexistent_laya_fixture", "arguments": "{}"}
            else:
                item = {"type": "message", "id": "answer", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": "Native fixture complete.", "annotations": []}]}
            response = {"id": f"fixture-{index}", "object": "response", "status": "completed",
                        "output": [item], "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                                                   "input_tokens_details": {"cached_tokens": 0}}}
            events = [{"type": "response.created", "response": {"id": response["id"]}},
                      {"type": "response.output_item.done", "output_index": 0, "item": item},
                      {"type": "response.completed", "response": response}]
            payload = "".join(map(sse, events)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    with tempfile.TemporaryDirectory(prefix="laya-native-fixture-") as temporary:
        root = Path(temporary)
        (root / "home").mkdir()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = {**os.environ, "CODEX_HOME": str(root / "home"),
               "LAYA_CONTROLLER_PYTHON": str(root / "missing-python") if args.missing_worker else sys.executable,
               "LAYA_CONTROLLER_LOG_DIR": str(root / "decisions")}
        # A custom fixture provider has no auth and no external endpoint.
        command = [str(args.binary.resolve()), "--enable", "step_model_switching", "--enable",
                   "reasoning_effort_override", "exec", "--ignore-user-config", "--skip-git-repo-check",
                   "--json", "-s", "read-only", "-C", str(root), "-m", "laya-astra",
                   "-c", 'model_provider="fixture"', "-c", 'model_reasoning_effort="medium"',
                   "-c", 'model_providers.fixture.name="OpenAI"',
                   "-c", f'model_providers.fixture.base_url="http://127.0.0.1:{server.server_port}/v1"',
                   "-c", 'model_providers.fixture.wire_api="responses"',
                   "-c", 'model_providers.fixture.supports_websockets=false',
                   "Inspect a failing test; do not deploy. Report unresolved failures."]
        if args.unified:
            command[:1] = [sys.executable, "-I", "-m", "laya_codex_companion"]
            model_index = command.index("-m", 4)
            del command[model_index:model_index + 2]
        start = time.perf_counter()
        try:
            completed = subprocess.run(command, env=env, input="", capture_output=True, text=True, encoding="utf-8", timeout=240)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        records = []
        logs = list((root / "decisions").glob("*.jsonl"))
        if args.unified:
            events = [json.loads(line) for line in completed.stdout.splitlines() if line.startswith("{")]
            thread_id = next((e["thread_id"] for e in events if e.get("type") == "thread.started"), None)
            logs = [native_root / "logs" / (thread_id + ".jsonl")] if thread_id else []
        for log in logs:
            records += [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        checks = {"exit_success": completed.returncode == 0, "three_generations": len(requests) == 3,
                  "alias_not_sent_to_provider": bool(requests) and all(r["model"] == "gpt-6-astra" for r in requests),
                  "audited_capture": bool(records) and all(r["applied"] for r in records)}
        if args.missing_worker:
            checks["explicit_fallback"] = bool(records) and records[0]["decision"]["status"] == "fallback"
        else:
            checks["real_local_decisions"] = bool(records) and all(r["decision"]["status"] == "decided" for r in records)
            checks["tool_errors_invalidate_lease"] = [r["decision"]["generation"] for r in records] == [1, 2, 3]
            checks["request_effort_stays_pinned"] = bool(requests) and len({r.get("reasoning", {}).get("effort") for r in requests}) == 1
            checks["native_configuration_update_used"] = any(i.get("type") == "configuration_update"
                                                              for r in requests for i in r.get("input", []))
            # Verify provider input, not merely an APPLIED UI message. The upstream
            # request-level effort is pinned for caching; tail updates are effective.
            for record in records:
                generation = record["decision"]["generation"]
                if not 1 <= generation <= len(requests):
                    checks["wire_matches_capture"] = False
                    break
                body = requests[generation - 1]
                effort = body.get("reasoning", {}).get("effort")
                for item in body.get("input", []):
                    if item.get("type") == "configuration_update":
                        effort = item.get("reasoning", {}).get("effort", effort)
                checks["wire_matches_capture"] = effort == record["actual_effort"]
                if not checks["wire_matches_capture"]:
                    break
        with args.binary.open("rb") as binary_file:
            binary_sha256 = hashlib.file_digest(binary_file, "sha256").hexdigest()
        report = {"timestamp": datetime.now(timezone.utc).isoformat(), "fixture": "local-responses-three-generations",
                  "binary_sha256": binary_sha256,
                  "real_openai_generations": False, "real_laya_inference": not args.missing_worker,
                  "unified_cli": args.unified,
                  "elapsed_seconds": round(time.perf_counter() - start, 3), "checks": checks,
                  "decisions": records, "request_count": len(requests),
                  "wire": [{"model": r.get("model"), "reasoning": r.get("reasoning"),
                            "updates": [i for i in r.get("input", []) if i.get("type") == "configuration_update"]}
                           for r in requests]}
        if not all(checks.values()):
            print(completed.stderr[-6000:], file=sys.stderr)
            print(completed.stdout[-6000:], file=sys.stderr)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(checks))
        return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
