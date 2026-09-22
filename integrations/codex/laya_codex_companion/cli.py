import argparse
import json
import os
import sys
from pathlib import Path

from .config import home


def main():
    parser = argparse.ArgumentParser(prog="laya-for-codex")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="Run the offline stdio MCP server")
    commands.add_parser("doctor", help="Inspect installation without loading PyTorch")
    prepare = commands.add_parser("prepare", help="Download pinned checkpoints explicitly")
    prepare.add_argument("--model", choices=["multilingual", "english", "typed-decisions", "all"], default="multilingual")
    prepare.add_argument("--source-cache", type=Path, help="Read existing pinned Hugging Face snapshots without downloading")
    predict = commands.add_parser("predict", help="Evaluate a JSON request (single or batch)")
    predict.add_argument("file", type=Path)
    predict.add_argument("--require-device", choices=["cpu", "cuda", "mps"],
                         help="Fail validation if inference falls back to a different device")
    benchmark = commands.add_parser("benchmark", help="Explicit synthetic diagnostic")
    benchmark.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            from .server import serve
            serve()
            return 0
        if args.command == "prepare":
            os.environ.update(USE_TF="0", USE_TORCH="1", HF_HUB_DISABLE_TELEMETRY="1")
            from .checkpoints import prepare
            result = prepare(home(), args.model, args.source_cache)
        else:
            from .runtime import Runtime
            runtime = Runtime()
            try:
                if args.command == "doctor":
                    result = runtime.status()
                elif args.command == "benchmark":
                    result = runtime.benchmark(args.iterations)
                else:
                    request = json.loads(args.file.read_text(encoding="utf-8"))
                    result = (runtime.predict_batch if "items" in request else runtime.predict)(**request)
                    if args.require_device:
                        predictions = [item.get("result") for item in result["items"]] if "items" in result else [result]
                        for prediction in predictions:
                            if prediction is None:
                                raise RuntimeError("Device verification requires a successful result for every item")
                            actual = prediction["runtime"].get("device") or prediction.get("original_runtime", {}).get("device")
                            if actual != args.require_device:
                                raise RuntimeError(f"Required {args.require_device}, actual device {actual}; requested device was not verified")
            finally:
                runtime.close()
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, RuntimeError, MemoryError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
