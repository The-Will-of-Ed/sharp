"""MCP transport for the shared operation catalog."""

import json
from functools import partial

from pydantic import TypeAdapter

from .operations import build_operations


def build_server(root):
    import anyio
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import CallToolResult, TextContent

    catalog = build_operations(root)

    class OperationServer(MCPServer):
        async def list_tools(self):
            tools = await super().list_tools()
            for tool in tools:
                tool.input_schema = TypeAdapter(catalog[tool.name]).json_schema()
            return tools

        async def call_tool(self, name, arguments, context=None):
            # Dispatch raw arguments to the shared validator: SDK coercion must
            # not discard unknown fields or turn strings into lists first.
            try:
                result = await anyio.to_thread.run_sync(partial(catalog[name], **arguments))
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
                )
            except (ValueError, OSError, KeyError, TypeError) as exc:
                raise ToolError(str(exc)) from exc

    server = OperationServer(
        "Sharp",
        instructions="Use contracts_describe. Never infer user confidence or silently approve facts. Custom rules use customization_manage, not core source edits.",
    )
    for operation in catalog.values():
        server.tool()(operation)
    return server


def serve(root):
    build_server(root).run(transport="stdio")
