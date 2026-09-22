"""Verify Windows MCP client -> WSL stdio -> actual Linux CUDA inference."""
import argparse
import asyncio
import json
from pathlib import Path
import platform
import shutil

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(args):
    executable = shutil.which("wsl.exe")
    if not executable:
        raise RuntimeError("Run this test from Windows with WSL installed")
    params = StdioServerParameters(command=executable, args=["-d", args.distro, "--", args.python,
                                                            "-m", "laya_codex_companion", "serve"])
    report = {"client_platform": platform.platform(), "distro": args.distro, "errors": []}
    def unpack(result):
        if result.isError:
            raise RuntimeError(str(result.content))
        return result.structuredContent or json.loads(next(c.text for c in result.content if c.type == "text"))
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                report["tools"] = [tool.name for tool in (await session.list_tools()).tools]
                assert len(report["tools"]) == 8
                report["status"] = unpack(await session.call_tool("laya_status", {}))
                report["prediction"] = unpack(await session.call_tool("laya_predict", {
                    "state": "The football team won the championship.", "use_cache": False,
                    "questions": {"topic": {"type": "choice", "instructions": "What is the topic?",
                                             "criteria": ["sports", "science"]}}}))
                assert report["prediction"]["runtime"]["device"] == "cuda", "Actual CUDA required"
                assert report["prediction"]["answers"]["topic"]["choice"] == "sports"
                report["release"] = unpack(await session.call_tool("laya_release", {}))
    except Exception as exc:
        report["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"errors": report["errors"], "output": str(args.output)}))
    return bool(report["errors"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distro", default="Debian")
    parser.add_argument("--python", required=True, help="Absolute Linux path to the prepared venv Python")
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(asyncio.run(run(parser.parse_args())))
