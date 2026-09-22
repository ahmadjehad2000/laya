"""Real MCP transport and labeled predictions. No downloads or config mutation."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def unpack(result):
    if result.isError:
        raise RuntimeError("; ".join(getattr(item, "text", "") for item in result.content))
    if result.structuredContent:
        return result.structuredContent
    return json.loads(next(item.text for item in result.content if item.type == "text"))


async def smoke(args):
    environment = {**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT.parents[1]), "USE_TF": "0"}
    if args.installed:
        environment.pop("PYTHONPATH", None)
    if args.device:
        environment["LAYA_COMPANION_DEVICE"] = args.device
    if args.model:
        environment["LAYA_COMPANION_MODEL"] = args.model
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
              "python": platform.python_version(), "integration_failures": [], "prediction_failures": [], "groups": []}
    params = StdioServerParameters(command=sys.executable, args=["-m", "laya_codex_companion", "serve"], env=environment)
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                report["tools"] = [t.name for t in (await session.list_tools()).tools]
                assert len(report["tools"]) == 7

                async def call(tool, request):
                    return unpack(await session.call_tool(tool, request))

                report["initial_status"] = await call("laya_status", {})
                with tempfile.TemporaryDirectory() as temporary:
                    folder = Path(temporary)
                    (folder / "records.json").write_text(json.dumps([
                        {"id": "sports", "state": "The football team won the championship."},
                        {"id": "science", "state": "Scientists discovered a new planet."}]), encoding="utf-8")
                    report["file_offload"] = await call("laya_classify_file", {
                        "workspace": temporary, "input_path": "records.json", "questions": {
                            "topic": {"type": "choice", "instructions": "What is the topic?", "criteria": ["sports", "science"]}}})
                    assert report["file_offload"]["records"] == 2
                    assert report["file_offload"]["failed"] == 0
                    assert Path(report["file_offload"]["artifact"]).is_file()
                    if args.require_device:
                        assert report["file_offload"]["devices"] == [args.require_device]
                    (folder / "chat.json").write_text(json.dumps([
                        {"role": "user", "content": "Do not deploy"},
                        {"role": "tool", "content": "old data " * 3000},
                        {"role": "user", "content": "Continue tests"}]), encoding="utf-8")
                    report["local_handoff"] = await call("laya_compact_file", {
                        "workspace": temporary, "input_path": "chat.json", "keep_recent": 1})
                    assert report["local_handoff"]["archived_tool_outputs"] == 1
                    assert report["local_handoff"]["handoff_bytes"] < report["local_handoff"]["original_context_bytes"]
                request = json.loads((ROOT / "examples" / "quickstart.json").read_text(encoding="utf-8"))
                report["quickstart"] = await call("laya_predict", request)
                assert {a["type"] for a in report["quickstart"]["answers"].values()} == {"choice", "score", "noul"}
                if args.require_device:
                    assert report["quickstart"]["runtime"]["device"] == args.require_device, "Unexpected device fallback"
                request["use_cache"] = True
                await call("laya_predict", request)
                cached = await call("laya_predict", request)
                assert cached["runtime"]["cache_hit"] and cached["runtime"]["inference_ms"] == 0
                report["cache_verified"] = True
                partial = await call("laya_predict_batch", {"questions": request["questions"], "items": [
                    {"id": "good", "state": request["state"]}, {"id": "oversized", "state": "word " * 3000}]})
                assert partial["succeeded"] == 1 and partial["failed"] == 1
                report["partial_failure_verified"] = True
                fixture = json.loads((ROOT / "examples" / "evaluation.json").read_text(encoding="utf-8"))
                report["fixture_version"] = fixture["version"]
                for group in fixture["groups"]:
                    result = await call("laya_predict_batch", {"items": [{"id": c["id"], "state": c["state"]} for c in group["cases"]],
                                                               "questions": group["questions"], "use_cache": False})
                    summary = {"name": group["name"], "correct": 0, "total": 0, "cases": []}
                    for case, prediction in zip(group["cases"], result["items"], strict=True):
                        record = {"id": case["id"], "evidence": case["evidence"], "expected": case["expected"], **prediction}
                        if "error" in prediction:
                            report["integration_failures"].append(record)
                        else:
                            if args.require_device:
                                assert prediction["result"]["runtime"]["device"] == args.require_device, "Unexpected device fallback"
                            for qid, expected in case["expected"].items():
                                answer = prediction["result"]["answers"][qid]
                                actual = answer["choice"] if answer["type"] == "choice" else answer["noul"] >= 0.5
                                summary["total"] += 1
                                summary["correct"] += actual == expected
                                if actual != expected:
                                    report["prediction_failures"].append({"id": case["id"], "question": qid,
                                                                          "expected": expected, "actual": actual,
                                                                          "evidence": case["evidence"]})
                        summary["cases"].append(record)
                    report["groups"].append(summary)
                await call("laya_release", {})
                report["released_status"] = await call("laya_status", {})
                assert report["released_status"]["loaded"] == []
                assert report["released_status"]["cache_entries"] == 0
    except Exception as exc:
        report["integration_failures"].append({"type": type(exc).__name__, "message": str(exc)})
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({"integration_failures": len(report["integration_failures"]),
                      "prediction_failures": len(report["prediction_failures"]),
                      "groups": [{k: g[k] for k in ("name", "correct", "total")} for g in report["groups"]],
                      "output": str(args.output)}, indent=2))
    return 1 if report["integration_failures"] else (2 if report["prediction_failures"] else 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", action="store_true", help="Test the installed companion instead of the source checkout")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda", "mps", "auto"])
    parser.add_argument("--model", choices=["multilingual", "english", "typed-decisions", "auto"])
    parser.add_argument("--require-device", choices=["cpu", "cuda", "mps"], help="Fail if real inference falls back to another device")
    raise SystemExit(asyncio.run(smoke(parser.parse_args())))
