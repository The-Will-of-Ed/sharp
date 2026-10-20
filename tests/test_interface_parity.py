"""The same operations, contracts and workspace boundaries through CLI and MCP."""

import asyncio
import json
import os
import re
import subprocess
import sys

import pytest
from pydantic import TypeAdapter


def cli(root, name, arguments=None, *, schema=False):
    command = [sys.executable, "-m", "sharp", name, "--root", str(root)]
    command += ["--schema"] if schema else ["--args", json.dumps(arguments or {})]
    return subprocess.run(command, capture_output=True, encoding="utf-8")


def unpack(result):
    assert not result.is_error, str(result)
    if result.structured_content is not None:
        return result.structured_content
    values = [json.loads(c.text) for c in result.content if c.type == "text"]
    return values[0] if len(values) == 1 else values


def test_every_operation_has_one_cli_and_mcp_contract(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    from sharp.operations import build_operations

    catalog = build_operations(tmp_path)
    help_text = subprocess.check_output([sys.executable, "-m", "sharp", "--help"], encoding="utf-8")
    names = {name.strip() for name in re.search(r"\{([^}]+)\}", help_text).group(1).split(",")}
    assert names == set(catalog) | {"mcp"}

    async def run():
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sharp", "mcp", "--root", str(tmp_path)],
            env=os.environ.copy(),
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = (await client.list_tools()).tools
                assert {t.name for t in tools} == set(catalog)
                for tool in tools:
                    result = cli(tmp_path, tool.name, schema=True)
                    assert result.returncode == 0, result.stderr
                    schema = json.loads(result.stdout)
                    assert schema == TypeAdapter(catalog[tool.name]).json_schema()
                    mcp_schema = tool.model_dump(by_alias=True)["inputSchema"]
                    assert schema == mcp_schema

    asyncio.run(run())


def test_cli_mcp_result_validation_and_scope_parity(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    initialized = cli(tmp_path, "workspace_initialize")
    assert initialized.returncode == 0, initialized.stderr
    (tmp_path / "source.txt").write_text("Built a Python service.", encoding="utf-8")
    argument_file = tmp_path / "arguments.json"
    argument_file.write_text(json.dumps({"paths": ["source.txt"]}), encoding="utf-8")
    from_file = subprocess.run(
        [
            sys.executable,
            "-m",
            "sharp",
            "material_extract",
            "--root",
            str(tmp_path),
            "--args",
            "@" + str(argument_file),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    assert from_file.returncode == 0, from_file.stderr
    assert json.loads(from_file.stdout)[0]["text"] == "Built a Python service."

    async def run():
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sharp", "mcp", "--root", str(tmp_path)],
            env=os.environ.copy(),
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                for name, args in [
                    ("career_inspect", {}),
                    ("settings_inspect", {}),
                    ("contracts_describe", {"names": ["Career"]}),
                    ("material_extract", {"paths": ["source.txt"]}),
                ]:
                    result = cli(tmp_path, name, args)
                    assert result.returncode == 0, result.stderr
                    mcp = unpack(await client.call_tool(name, args))
                    assert json.loads(result.stdout) == mcp
                current = unpack(await client.call_tool("settings_inspect", {}))
                updated = cli(
                    tmp_path,
                    "settings_update",
                    {
                        "settings_path": "settings.local.yaml",
                        "expected_hash": current["hash"],
                        "changes": {"styles.body.size": 9.5},
                    },
                )
                assert updated.returncode == 0, updated.stderr
                assert json.loads(updated.stdout) == unpack(
                    await client.call_tool("settings_inspect", {})
                )
                for name, args in [
                    ("career_inspect", {"career_path": "../outside.yaml"}),
                    ("material_extract", {"paths": "source.txt"}),
                    ("career_inspect", {"unexpected": True}),
                ]:
                    result = cli(tmp_path, name, args)
                    assert result.returncode == 2
                    assert (await client.call_tool(name, args)).is_error

    asyncio.run(run())


def test_shared_demo_and_migration_preserve_cli_only_features(tmp_path):
    from sharp.operations import build_operations

    operations = build_operations(tmp_path)
    demo = operations["document_demo"]()
    assert demo
    assert list((tmp_path / "outputs/demo").glob("*.pdf"))
    migrated = operations["career_migrate"](
        source="outputs/demo/career.json", destination="imported.yaml"
    )
    assert migrated["path"] == str(tmp_path / "imported.yaml")
    assert operations["career_inspect"](career_path="imported.yaml")["career"]["basics"]["name"]
    with pytest.raises(ValueError, match="Destination exists"):
        operations["career_migrate"](source="outputs/demo/career.json", destination="imported.yaml")
