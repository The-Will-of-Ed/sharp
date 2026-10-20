import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from sharp.adapters.providers import ACPChooser


def test_acp_uses_installed_sdk_capabilities_and_streamed_message(monkeypatch, tmp_path):
    import acp
    from acp.schema import ClientCapabilities

    class Connection:
        async def initialize(self, **kwargs):
            assert isinstance(kwargs["client_capabilities"], ClientCapabilities)

        async def new_session(self, **kwargs):
            assert kwargs["mcp_servers"] == []
            return SimpleNamespace(session_id="test")

        async def prompt(self, **kwargs):
            await self.client.session_update("test", SimpleNamespace(
                session_update="agent_message_chunk", content=SimpleNamespace(type="text", text='{"ranked":[]}')))
            return SimpleNamespace(stop_reason="end_turn")

    @asynccontextmanager
    async def spawn(client, command, *args, **kwargs):
        assert "CODEX_SANDBOX_NETWORK_DISABLED" not in kwargs["env"]
        await client.ext_notification("auth/status_update", {"status": "authenticated"})
        connection = Connection()
        connection.client = client
        yield connection, None

    monkeypatch.setattr(acp, "spawn_agent_process", spawn)
    chooser = ACPChooser("node", ["adapter.js"], cwd=str(tmp_path))
    assert asyncio.run(chooser._ask("Choose")) == '{"ranked":[]}'
    assert "initialize_s" in chooser.timings
