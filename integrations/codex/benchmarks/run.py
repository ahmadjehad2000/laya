"""Portable MCP benchmark: public classification, synthetic primitives, latency and cache.

Uses prepared checkpoints only, records requested versus actual device, and never changes
the installed configuration. Run one device at a time to avoid resource contention.
"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

import psutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
COMPANION = HERE.parent
REPO = COMPANION.parents[1]
sys.path.insert(0, str(COMPANION))
from benchmarks import ag_news  # noqa: E402
from benchmarks.metrics import classification, latency, rubric_metrics  # noqa: E402

PERF_QUESTIONS = {"category": {"type": "choice", "instructions": "Classify the support request.",
                              "criteria": {"billing": "payments and refunds", "technical": "software failures",
                                           "sales": "new purchases", "other": "none of these"}}}
SHORT = "The application crashes when opening the settings page. Please fix the error."
STATES = {"short": SHORT, "medium": SHORT * 8, "long": SHORT * 24}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host_info():
    cpu = platform.processor()
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    elif Path("/proc/cpuinfo").exists():
        cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")), cpu)
    gpu = None
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            gpu = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"platform": platform.platform(), "python": platform.python_version(), "cpu": cpu,
            "linux_distribution": platform.freedesktop_os_release() if sys.platform.startswith("linux") else None,
            "physical_cores": psutil.cpu_count(logical=False), "logical_cores": psutil.cpu_count(),
            "ram_total_gib": psutil.virtual_memory().total / 2**30,
            "ram_available_start_gib": psutil.virtual_memory().available / 2**30,
            "gpu_driver_total_vram": gpu,
            "packages": {p: importlib.metadata.version(p) for p in ("torch", "transformers", "numpy", "mcp", "laya")}}


def unpack(response):
    if response.isError:
        raise RuntimeError("; ".join(getattr(c, "text", "") for c in response.content))
    return response.structuredContent or json.loads(next(c.text for c in response.content if c.type == "text"))


async def timed(session, tool, arguments):
    start = time.perf_counter()
    result = unpack(await session.call_tool(tool, arguments))
    return result, (time.perf_counter() - start) * 1000


def require_device(result, device):
    actual = result["runtime"].get("device")
    if actual != device:
        raise RuntimeError(f"Requested {device}, observed {actual}; refuse mislabeled device benchmark")


async def quality(session, args, report):
    selected = ag_news.load(args.dataset, args.per_class, args.seed)
    records = []
    for offset in range(0, len(selected), 8):
        chunk = selected[offset:offset + 8]
        response, elapsed = await timed(session, "laya_predict_batch", {
            "items": [{"id": c["id"], "state": c["state"]} for c in chunk],
            "questions": ag_news.QUESTIONS, "use_cache": False, "model": args.model})
        for case, item in zip(chunk, response["items"], strict=True):
            assert item["id"] == case["id"]
            record = {"id": case["id"], "row_index": case["row_index"], "expected": case["expected"],
                      "predicted": None, "batch_client_ms": elapsed}
            if "error" in item:
                record["error"] = item["error"]
            else:
                result = item["result"]
                require_device(result, args.device)
                record.update(predicted=result["answers"]["topic"]["choice"],
                              confidence=result["answers"]["topic"]["confidence"],
                              context_tokens=result["context_tokens"], runtime=result["runtime"])
            records.append(record)
        print(f"AG News {len(records)}/{len(selected)}", flush=True)
    report["ag_news"] = {"provenance": "Public test subset; no claim about training-data contamination",
                         "source_url": ag_news.URL, "sha256": ag_news.SHA256,
                         "seed": args.seed, "per_class": args.per_class, "questions": ag_news.QUESTIONS,
                         "selection": "Python Random(seed); sample each class in fixed label order; shuffle combined selection",
                         "preprocessing": "CSV title + space + description; no summarization or truncation",
                         "metrics": classification([r["expected"] for r in records], [r["predicted"] for r in records], ag_news.LABELS),
                         "errors": sum("error" in r for r in records), "records": records}
    fixture_path = COMPANION / "examples/evaluation.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    synthetic = {"sha256": sha(fixture_path), "version": fixture["version"], "groups": []}
    for group in fixture["groups"]:
        response, _ = await timed(session, "laya_predict_batch", {
            "items": [{"id": c["id"], "state": c["state"]} for c in group["cases"]],
            "questions": group["questions"], "use_cache": False, "model": args.model})
        correct = total = failures = 0
        binary = []
        details = []
        for case, item in zip(group["cases"], response["items"], strict=True):
            assert item["id"] == case["id"]
            if "result" in item:
                require_device(item["result"], args.device)
            else:
                failures += 1
            for qid, expected in case["expected"].items():
                answer = item.get("result", {}).get("answers", {}).get(qid)
                actual = None
                if answer:
                    if answer["type"] == "choice":
                        actual = answer["choice"]
                    else:
                        actual = answer["noul"] >= .5
                        binary.append((float(expected), answer["noul"]))
                total += 1
                correct += actual == expected
                details.append({"id": case["id"], "question": qid, "expected": expected, "predicted": actual,
                                "evidence": case["evidence"], "answer": answer, "error": item.get("error")})
        synthetic["groups"].append({"name": group["name"], "correct": correct, "total": total, "record_errors": failures,
                                    "binary_valid_n": len(binary),
                                    "binary_brier_valid": statistics.mean((p - y)**2 for y, p in binary) if binary else None,
                                    "records": details})
    report["synthetic"] = synthetic
    rubric_path = HERE / "rubric.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    response, _ = await timed(session, "laya_predict_batch", {
        "items": [{"id": c["id"], "state": c["state"]} for c in rubric["cases"]],
        "questions": rubric["questions"], "use_cache": False, "model": args.model})
    predicted = []
    for case, item in zip(rubric["cases"], response["items"], strict=True):
        assert item["id"] == case["id"]
        if "result" in item:
            require_device(item["result"], args.device)
        predicted.append(item.get("result", {}).get("answers", {}).get("severity", {}).get("score"))
    report["rubric"] = {"sha256": sha(rubric_path), "metrics": rubric_metrics([c["expected"] for c in rubric["cases"]], predicted, 4),
                        "results": response, "scope": rubric["provenance"]}


async def performance(session, args, report):
    perf = {}
    for name, state in STATES.items():
        request = {"state": state, "questions": PERF_QUESTIONS, "use_cache": False, "model": args.model}
        for _ in range(args.warmup):
            result, _ = await timed(session, "laya_predict", request)
            require_device(result, args.device)
        wall, internal = [], []
        for _ in range(args.samples):
            result, elapsed = await timed(session, "laya_predict", request)
            require_device(result, args.device)
            wall.append(elapsed)
            internal.append(result["runtime"]["inference_ms"])
        perf[name] = {"client": latency(wall), "model_inference": latency(internal),
                      "context_tokens": result["context_tokens"], "input": request}
        print(f"Warm {name}: p50={perf[name]['client']['p50_ms']:.1f} ms", flush=True)
    cached_request = {"state": SHORT, "questions": PERF_QUESTIONS, "use_cache": True, "model": args.model}
    await timed(session, "laya_predict", cached_request)
    hits = []
    for _ in range(args.samples):
        result, elapsed = await timed(session, "laya_predict", cached_request)
        assert result["runtime"]["cache_hit"]
        hits.append(elapsed)
    perf["cache_hit"] = {"client": latency(hits), "scope": "Warm exact-result cache; no model inference"}
    questions = {**PERF_QUESTIONS,
                 "refund": {"type": "noul", "instructions": "The customer explicitly requests a refund."},
                 "severity": {"type": "score", "instructions": "Rate the impact.",
                              "criteria": ["cosmetic issue", "some work blocked", "complete outage"]}}
    values = []
    for _ in range(args.batch_repeats):
        result, elapsed = await timed(session, "laya_predict", {"state": SHORT, "questions": questions,
                                                                 "use_cache": False, "model": args.model})
        require_device(result, args.device)
        values.append(elapsed)
    perf["three_questions"] = {"client": latency(values), "questions": questions}
    for count in (1, 8):
        items = [{"id": str(i), "state": SHORT} for i in range(count)]
        values = []
        for _ in range(args.batch_repeats):
            result, elapsed = await timed(session, "laya_predict_batch", {
                "items": items, "questions": PERF_QUESTIONS, "use_cache": False, "model": args.model})
            if result["failed"]:
                raise RuntimeError(f"Batch benchmark failed: {result}")
            for item in result["items"]:
                require_device(item["result"], args.device)
            values.append(elapsed)
        perf[f"batch_{count}"] = {"client": latency(values), "records_per_call": count,
                                  "records_per_second": count * len(values) / (sum(values) / 1000)}
    report["performance"] = perf


async def run(args):
    # Validate data before any model work; no implicit downloads.
    ag_news.load(args.dataset, args.per_class, args.seed)
    report = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(),
              "host": host_info(), "requested_device": args.device, "requested_model": args.model,
              "settings": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
              "cold_processes": [], "errors": [],
              "harness_sha256": {p.name: sha(p) for p in sorted(HERE.glob("*.py"))},
              "runtime_sha256": {p.name: sha(p) for p in sorted((COMPANION / "laya_codex_companion").glob("*.py"))}}
    env = {**os.environ, "PYTHONPATH": str(COMPANION) + os.pathsep + str(REPO),
           "LAYA_COMPANION_DEVICE": args.device, "LAYA_COMPANION_MODEL": args.model, "USE_TF": "0"}
    params = StdioServerParameters(command=sys.executable, args=["-m", "laya_codex_companion", "serve"], env=env)
    try:
        for trial in range(args.cold_runs):
            start = time.perf_counter()
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(minutes=10)) as session:
                    await session.initialize()
                    initialize_ms = (time.perf_counter() - start) * 1000
                    status, _ = await timed(session, "laya_status", {})
                    report["configuration"] = status["configuration"]
                    result, elapsed = await timed(session, "laya_predict", {
                        "state": SHORT, "questions": PERF_QUESTIONS, "use_cache": False, "model": args.model})
                    require_device(result, args.device)
                    report["checkpoint"] = result["checkpoint"]
                    report["actual_device"] = result["runtime"]["device"]
                    report["cold_processes"].append({"initialize_ms": initialize_ms, "first_predict_client_ms": elapsed,
                                                     "total_ms": initialize_ms + elapsed, "runtime": result["runtime"]})
                    print(f"Cold process {trial+1}/{args.cold_runs}: {initialize_ms + elapsed:.0f} ms", flush=True)
                    if trial == args.cold_runs - 1:
                        await performance(session, args, report)
                        await quality(session, args, report)
                        report["resident_status"], _ = await timed(session, "laya_status", {})
                    await timed(session, "laya_release", {})
                    final, _ = await timed(session, "laya_status", {})
                    assert not final["loaded"] and not final["cache_entries"]
                    report["release_verified"] = True
    except Exception as exc:
        report["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "errors": report["errors"],
                      "ag_news": report.get("ag_news", {}).get("metrics")}, indent=2))
    return bool(report["errors"]) or bool(report.get("ag_news", {}).get("errors")) or any(
        g["record_errors"] for g in report.get("synthetic", {}).get("groups", [])) or bool(report.get("rubric", {}).get("metrics", {}).get("errors"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"], required=True)
    parser.add_argument("--model", choices=["multilingual", "english", "typed-decisions"], default="multilingual")
    parser.add_argument("--dataset", type=Path, default=ag_news.DEFAULT_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-class", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--cold-runs", type=int, default=3)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--batch-repeats", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.cold_runs <= 10 or not 5 <= args.samples <= 1000 or not 1 <= args.warmup <= 50 or not 2 <= args.batch_repeats <= 100:
        parser.error("cold-runs 1–10, samples 5–1000, warmup 1–50, batch-repeats 2–100")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
