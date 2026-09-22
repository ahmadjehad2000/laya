"""Cross-platform installer. Standard library only until the isolated runtime exists."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
import venv

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
NAME = "laya-for-codex"
BEGIN, END = "# BEGIN LAYA-FOR-CODEX", "# END LAYA-FOR-CODEX"
OLD_BEGIN, OLD_END = "# BEGIN LAYA-CODEX MANAGED MCP", "# END LAYA-CODEX MANAGED MCP"


def run(args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def python_at(root):
    return root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace_block(text, begin, end, replacement=""):
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise ValueError("Ambiguous managed configuration markers; no edits made")
    if begin not in text:
        return text + ("\n" + replacement if replacement else "")
    return re.sub(re.escape(begin) + r"[\s\S]*?" + re.escape(end), lambda _: replacement, text, count=1)


def config_change(path, root, transform):
    """Back up exact bytes and reject races; record a guarded rollback receipt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    before = path.read_bytes() if path.exists() else b""
    after = transform(before.decode("utf-8")).encode("utf-8")
    tomllib.loads(after.decode("utf-8"))
    if before == after:
        return None
    root.mkdir(parents=True, exist_ok=True)
    backup = root / f"config-{time.time_ns()}.toml.bak"
    backup.write_bytes(before)
    if (path.read_bytes() if path.exists() else b"") != before:
        raise RuntimeError("Codex configuration changed concurrently; retry")
    temporary = path.with_name(path.name + ".laya-tmp")
    temporary.write_bytes(after)
    os.replace(temporary, path)
    receipt = {"config": str(path), "backup": str(backup), "after_sha256": digest(after)}
    (root / "rollback.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def mcp_entry(root):
    return {"command": str(python_at(root)), "args": ["-m", "laya_codex_companion", "serve"],
            "env": {"LAYA_COMPANION_HOME": str(root), "HF_HUB_OFFLINE": "1",
                    "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
                    "TOKENIZERS_PARALLELISM": "false", "USE_TF": "0"}}


def direct_block(root):
    entry = mcp_entry(root)
    lines = [BEGIN, f"[mcp_servers.{NAME}]", f"command = {json.dumps(entry['command'])}",
             f"args = {json.dumps(entry['args'])}", "startup_timeout_sec = 30", "tool_timeout_sec = 300",
             f"[mcp_servers.{NAME}.env]"]
    lines += [f"{key} = {json.dumps(value)}" for key, value in entry["env"].items()]
    return "\n".join([*lines, END])


def install_plugin(root, codex_home):
    # Materialize absolute executable paths in a separate generated local marketplace.
    marketplace_root = root / "marketplace"
    plugin = marketplace_root / "plugins" / NAME
    shutil.copytree(HERE / "plugins" / NAME, plugin, dirs_exist_ok=True)
    # Codex loads a cached copy; give each installed build an explicit cache key.
    for manifest in (plugin / "plugin.json", plugin / ".codex-plugin" / "plugin.json"):
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        metadata["version"] = metadata["version"].split("+")[0] + f"+codex.local-{time.time_ns()}"
        manifest.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    config = {"mcpServers": {NAME: mcp_entry(root)}}
    (plugin / ".mcp.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    portable = {"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                "mcpServers": {NAME: {"type": "stdio", **mcp_entry(root)}}}
    (plugin / "mcp.json").write_text(json.dumps(portable, indent=2), encoding="utf-8")
    catalog = marketplace_root / ".agents" / "plugins" / "marketplace.json"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(json.dumps({"name": "laya-companion", "interface": {"displayName": "Laya for Codex"},
                                  "plugins": [{"name": NAME, "source": {"source": "local", "path": f"./plugins/{NAME}"},
                                               "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                                               "category": "Productivity"}]}, indent=2), encoding="utf-8")
    environment = {**os.environ, "CODEX_HOME": str(codex_home)}
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex CLI missing; use --mode direct or install Codex before plugin registration")
    run([codex, "plugin", "marketplace", "add", marketplace_root], env=environment)
    run([codex, "plugin", "add", f"{NAME}@laya-companion"], env=environment)
    return catalog


def register(root, codex_home, mode, migrate):
    config = codex_home / "config.toml"
    text = config.read_text(encoding="utf-8") if config.exists() else ""
    parsed = tomllib.loads(text)
    servers = parsed.get("mcp_servers", {})
    if "laya" in servers and servers["laya"].get("enabled", True):
        if not migrate:
            raise RuntimeError("Existing Laya server detected. Use --migrate-existing after verifying this runtime")
        if OLD_BEGIN not in text:
            raise RuntimeError("Existing Laya registration is not managed; disable it manually before migration")
    if NAME in servers and BEGIN not in text:
        raise RuntimeError("An unmanaged laya-for-codex entry exists; configuration left unchanged")
    if mode == "direct" and any(
        key.startswith(NAME + "@") and value.get("enabled", True)
        for key, value in parsed.get("plugins", {}).items() if isinstance(value, dict)
    ):
        raise RuntimeError("The companion plugin is enabled. Uninstall it before switching to direct MCP")

    def transform(value):
        if migrate:
            value = replace_block(value, OLD_BEGIN, OLD_END)
        return replace_block(value, BEGIN, END, direct_block(root) if mode == "direct" else "")

    root.mkdir(parents=True, exist_ok=True)
    original = config.read_bytes() if config.exists() else b""
    receipt = config_change(config, root, transform)
    try:
        if mode == "plugin":
            # Capture config before the Codex CLI also updates it for plugin registration.
            backup = root / f"plugin-config-{time.time_ns()}.toml.bak"
            backup.write_bytes(original)
            receipt = receipt or {"config": str(config), "backup": str(backup)}
            catalog = install_plugin(root, codex_home)
            receipt["after_sha256"] = digest(config.read_bytes())
            (root / "rollback.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(f"Plugin marketplace: {catalog}")
    except Exception:
        # A failed plugin install must not strand the former managed registration.
        if receipt:
            config.write_bytes(Path(receipt["backup"]).read_bytes())
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install", "prepare", "doctor", "register", "uninstall", "rollback"], nargs="?", default="install")
    parser.add_argument("--home", type=Path, default=Path.home() / ".laya-for-codex")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--torch-index", choices=["cpu", "cu128", "default"], default="default")
    parser.add_argument("--model", choices=["multilingual", "english", "typed-decisions", "all"], default="multilingual")
    parser.add_argument("--mode", choices=["plugin", "direct", "none"], default="plugin")
    parser.add_argument("--migrate-existing", action="store_true")
    args = parser.parse_args()
    root, codex_home = args.home.expanduser().resolve(), args.codex_home.expanduser().resolve()
    python = python_at(root)
    environment = {**os.environ, "LAYA_COMPANION_HOME": str(root), "USE_TF": "0", "USE_TORCH": "1"}
    if args.command == "install":
        if not (3, 12) <= sys.version_info[:2] < (3, 14):
            raise RuntimeError("Use Python 3.12–3.13, preferably 3.12")
        root.mkdir(parents=True, exist_ok=True)
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(root / "venv")
        run([python, "-m", "pip", "install", "--upgrade", "pip"])
        torch_args = ["--index-url", f"https://download.pytorch.org/whl/{args.torch_index}"] if args.torch_index != "default" else []
        run([python, "-m", "pip", "install", "torch==2.11.0", *torch_args])
        run([python, "-m", "pip", "install", "-r", HERE / "requirements.lock"])
        run([python, "-m", "pip", "install", "--no-deps", REPO, HERE])
        path = root / "config.json"
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        settings.update(device=args.device, model="multilingual" if args.model == "all" else args.model)
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    if args.command in ("install", "prepare"):
        run([python, "-m", "laya_codex_companion", "prepare", "--model", args.model], env=environment)
    if args.command in ("install", "register"):
        # Real inference is required even for a registration-only migration.
        run([python, "-m", "laya_codex_companion", "predict", HERE / "examples" / "quickstart.json"], env=environment)
        if args.mode != "none":
            register(root, codex_home, args.mode, args.migrate_existing)
        print("Setup verified. Open a new local Codex session after registration.")
    elif args.command == "doctor":
        run([python, "-m", "laya_codex_companion", "doctor"], env=environment)
    elif args.command == "rollback":
        receipt = json.loads((root / "rollback.json").read_text(encoding="utf-8"))
        target = Path(receipt["config"])
        if digest(target.read_bytes()) != receipt["after_sha256"]:
            raise RuntimeError(f"Configuration changed since registration. Restore only the Laya sections from {receipt['backup']}")
        target.write_bytes(Path(receipt["backup"]).read_bytes())
        print("Previous configuration restored; prepared models retained.")
    elif args.command == "uninstall":
        codex = shutil.which("codex")
        if codex and (root / "marketplace").exists():
            run([codex, "plugin", "remove", f"{NAME}@laya-companion"], env={**os.environ, "CODEX_HOME": str(codex_home)})
        config_change(codex_home / "config.toml", root, lambda s: replace_block(s, BEGIN, END))
        print("Integration disconnected. Models, environment and backups retained.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
