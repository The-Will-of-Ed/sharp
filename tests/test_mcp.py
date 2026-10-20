import asyncio
import json
import os
import sys
from pathlib import Path
import pytest


def test_real_stdio_mcp_contract_discovery_and_workspace_scope(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    async def run():
        server = StdioServerParameters(command=sys.executable, args=["-m", "sharp", "mcp", "--root", str(tmp_path)], env=os.environ.copy())
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                assert "document_create" in {t.name for t in tools.tools}
                result = await client.call_tool("contracts_describe", {"names": ["BeforeInput", "Career"]})
                assert not result.is_error
                assert "confidence_levels" in str(result)
                initialized = await client.call_tool("workspace_initialize", {})
                assert not initialized.is_error
                assert (tmp_path / "settings.local.yaml").is_file()
                escape = await client.call_tool("career_inspect", {"career_path": "../outside.yaml"})
                assert escape.is_error
    asyncio.run(run())
