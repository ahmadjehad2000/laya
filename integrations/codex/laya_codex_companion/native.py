"""Launch the separately built native Codex with the local Laya controller."""
import json
import os
import subprocess
import sys

from .config import home


def has_model_option(args):
    """Respect argparse/clap short values and the end-of-options delimiter."""
    for arg in args:
        if arg == "--":
            break
        if arg in ("-m", "--model") or arg.startswith("--model="):
            return True
        if arg.startswith("-m") and not arg.startswith("--"):
            return True
    return False


def main():
    root = home() / "native"
    package = root
    try:
        if (root / "build.json").is_file():
            receipt = json.loads((root / "build.json").read_text(encoding="utf-8"))
            package = (root / receipt["package"]).resolve()
            package.relative_to(root.resolve())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Invalid native installation receipt: {exc}", file=sys.stderr)
        return 1
    binary = package / "bin" / ("codex.exe" if os.name == "nt" else "codex")
    if not binary.is_file():
        print("Native Codex is not built. Run: py -3.12 integrations/codex/native/build.py", file=sys.stderr)
        return 1
    env = {**os.environ, "LAYA_CONTROLLER_PYTHON": sys.executable,
           "LAYA_CONTROLLER_LOG_DIR": str(root / "logs")}
    # Use normal Codex authentication and permissions. CLI flags are invocation-only.
    args = sys.argv[1:]
    options = ["--enable", "step_model_switching", "--enable", "reasoning_effort_override"]
    if not has_model_option(args):
        options += ["-m", "laya-astra"]
    try:
        return subprocess.run([str(binary), *options, *args], env=env).returncode
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
