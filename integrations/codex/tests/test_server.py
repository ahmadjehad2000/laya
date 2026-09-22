import asyncio
import json

from laya_codex_companion.server import build_server


def test_tools_discovery_and_status():
    class Runtime:
        def status(self):
            return {"loaded": [], "device": None}

    async def check():
        server = build_server(Runtime())
        tools = await server.list_tools()
        assert {t.name for t in tools} == {"laya_context_file", "laya_status", "laya_predict", "laya_predict_batch", "laya_release", "laya_benchmark", "laya_classify_file", "laya_compact_file"}
        batch = next(t for t in tools if t.name == "laya_predict_batch")
        assert batch.annotations.readOnlyHint
        assert "items" in batch.inputSchema["required"]
        result = await server.call_tool("laya_status", {})
        assert "loaded" in json.dumps(result, default=str)

    asyncio.run(check())
