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


def integration_options():
    """Invocation-only MCP defaults; user CLI overrides are appended afterward."""
    settings = {
        "command": sys.executable,
        "args": ["-I", "-m", "laya_codex_companion", "serve"],
        "enabled": True,
        "startup_timeout_sec": 30,
        "tool_timeout_sec": 300,
        "env": {"LAYA_COMPANION_HOME": str(home()), "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1", "USE_TF": "0"},
    }
    options = []
    for key, value in settings.items():
        if isinstance(value, dict):
            for env_key, env_value in value.items():
                options += ["-c", f'mcp_servers.laya-for-codex.env.{env_key}={json.dumps(env_value)}']
        else:
            options += ["-c", f'mcp_servers.laya-for-codex.{key}={json.dumps(value)}']
    return options


def main(argv=None):
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
    env = {**os.environ, "LAYA_CONTROLLER_PYTHON": sys.executable, "LAYA_NATIVE_CONTROLLER": "1",
           "LAYA_CONTROLLER_LOG_DIR": str(root / "logs")}
    # Use normal Codex authentication and permissions. CLI flags are invocation-only.
    args = list(sys.argv[1:] if argv is None else argv)
    options = ["--enable", "step_model_switching", "--enable", "reasoning_effort_override"]
    options += integration_options()
    if not has_model_option(args):
        try:
            preference = root / "model.json"
            model = json.loads(preference.read_text(encoding="utf-8"))["model"] if preference.exists() else "laya-astra"
            if model not in ("laya-astra", "laya-sol"):
                raise ValueError("Expected laya-astra or laya-sol")
        except (ValueError, OSError, KeyError, TypeError) as exc:
            print(f"Invalid native model preference: {exc}", file=sys.stderr)
            return 1
        options += ["-m", model]
    try:
        return subprocess.run([str(binary), *options, *args], env=env).returncode
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
