"""Generate portable and compatibility manifests from one source of metadata."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "laya-for-codex"


def build():
    identity = {"name": "laya-for-codex", "version": "0.1.0",
                "description": "Local Laya decisions for developer triage, multilingual records, and explicit rubrics.",
                "author": {"name": "ahmadjehad2000", "url": "https://github.com/ahmadjehad2000"},
                "repository": "https://github.com/ahmadjehad2000/laya", "license": "Apache-2.0"}
    interface = {"displayName": "Laya for Codex", "shortDescription": "Local classification and rubric workflows.",
                 "longDescription": "Original Laya/PyTorch inference for concise, repeated decisions. Prepare the local runtime before enabling this plugin.",
                 "developerName": "ahmadjehad2000", "category": "Productivity", "capabilities": [],
                 "defaultPrompt": ["Triage these issues using Laya and show the supporting evidence.",
                                   "Classify these Arabic and English tickets.",
                                   "Score these records against my rubric."]}
    write(PLUGIN / ".codex-plugin" / "plugin.json", {**identity, "interface": interface,
                                                    "skills": "./skills/", "mcpServers": "./.mcp.json"})
    # Codex CLI 0.155.1 installs portable metadata but does not expose its MCP tools.
    # Keep the tested compatibility entrypoint active; package the portable manifest separately.
    write(PLUGIN / "plugin.portable.json", {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                                           **identity, "extensions": {"com.openai": {"interface": interface}}})
    server = {"command": "laya-for-codex", "args": ["serve"]}
    write(PLUGIN / ".mcp.json", {"mcpServers": {"laya-for-codex": server}})
    write(PLUGIN / "mcp.json", {"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                               "mcpServers": {"laya-for-codex": {"type": "stdio", **server}}})


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
