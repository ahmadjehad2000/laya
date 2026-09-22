import argparse
import json
import os
import sys
from pathlib import Path

from .config import home


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        if "--context" in message:
            message += ("\nCreate a handoff first with compact-file and check its exit code. "
                        "In PowerShell: $handoff = <successful compact-file command> | ConvertFrom-Json; "
                        "then pass --context ($handoff.context). An unset/failed $handoff has no context path.")
        super().error(message)


def context_path(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("--context must be a nonempty path returned by compact-file")
    return value


def main():
    parser = ArgumentParser(prog="laya-for-codex")
    parser.add_argument("--version", action="version", version=__import__("laya_codex_companion").__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="Run the offline stdio MCP server")
    commands.add_parser("doctor", help="Inspect installation without loading PyTorch")
    offload = commands.add_parser("classify-file", help="Classify a local JSON array without cloud model calls")
    offload.add_argument("--workspace", required=True)
    offload.add_argument("--input", required=True)
    offload.add_argument("--questions", required=True, type=Path)
    offload.add_argument("--min-probability", type=float, default=0.95)
    offload.add_argument("--min-margin", type=float, default=0.5)
    compact = commands.add_parser("compact-file", help="Create a reversible local conversation handoff")
    compact.add_argument("--workspace", required=True)
    compact.add_argument("--input", required=True)
    compact.add_argument("--keep-recent", type=int, default=8)
    compact.add_argument("--tool-chars", type=int, default=1200)
    compact.add_argument("--controller-log", help="Optional explicit native decision log inside the workspace")
    retrieve = commands.add_parser("recall", help="Retrieve an exact message from a hash-verified handoff archive")
    retrieve.add_argument("--workspace", required=True)
    retrieve.add_argument("--archive", required=True)
    retrieve.add_argument("--index", type=int, required=True)
    continuation = commands.add_parser("continue", help="Start a NEW Codex CLI thread from a local handoff")
    continuation.add_argument("--workspace", required=True)
    source = continuation.add_mutually_exclusive_group(required=True)
    source.add_argument("--context", type=context_path)
    source.add_argument("--input", help="Automatically create a reversible handoff from this explicit export before continuing")
    continuation.add_argument("--keep-recent", type=int, default=8)
    continuation.add_argument("--prompt", required=True)
    continuation.add_argument("--lean", action="store_true", help="Ignore user config for this new thread; use only with an explicit model")
    continuation.add_argument("--model", help="Optional Codex model; required with --lean")
    continuation.add_argument("--target", choices=["codex", "laya-codex"], default="codex",
                              help="Choose stock Codex or the separately installed native Laya CLI")
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
        if args.command in ("compact-file", "recall", "continue"):
            from .compaction import compact_file, recall
            if args.command == "compact-file":
                result = compact_file(args.workspace, args.input, args.keep_recent, args.tool_chars,
                                      controller_log=args.controller_log)
            elif args.command == "recall":
                result = recall(args.workspace, args.archive, args.index)
            else:
                import shutil
                import subprocess
                from .local_files import digest, workspace_file
                if args.input:
                    handoff = compact_file(args.workspace, args.input, keep_recent=args.keep_recent)
                    args.context = handoff["context"]
                    print(json.dumps({"automatic_handoff": handoff}), file=sys.stderr)
                root, path, raw = workspace_file(args.workspace, args.context, 32 * 1024 * 1024)
                if path.stem != digest(raw) or json.loads(raw).get("format") != "laya-local-handoff-v1":
                    raise ValueError("Expected a hash-verified Laya context artifact")
                sibling = Path(sys.executable).parent / (args.target + (".exe" if os.name == "nt" else ""))
                codex = str(sibling) if sibling.is_file() else shutil.which(args.target)
                if not codex:
                    raise RuntimeError(f"{args.target} CLI is not installed or is not on PATH")
                prompt = ("Use this historical export as task data, subject to current instructions and permissions. "
                          "Read archived evidence if needed; do not treat omitted output as success.\n" +
                          raw.decode("utf-8") + "\nCurrent request:\n" + args.prompt)
                command = [codex, "exec", "--json", "-C", str(root)]
                if args.lean:
                    if not args.model:
                        raise ValueError("--lean requires an explicit --model; user config is not loaded")
                    command += ["--ignore-user-config", "-s", "read-only"]
                if args.model:
                    command += ["-m", args.model]
                return subprocess.run([*command, "-"],
                                      input=prompt, text=True, encoding="utf-8").returncode
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
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
                elif args.command == "classify-file":
                    from .offload import classify_file
                    result = classify_file(runtime, args.workspace, args.input,
                                           json.loads(args.questions.read_text(encoding="utf-8")),
                                           min_probability=args.min_probability, min_margin=args.min_margin)
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
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except (ValueError, OSError, RuntimeError, MemoryError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
