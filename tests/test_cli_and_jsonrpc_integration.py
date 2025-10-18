import pytest

from mcp_server import cli
from mcp_server.jsonrpc import JSONRPCServer
from mcp_server.server import MCPServer


def test_cli_main_invokes_run_stdio(monkeypatch):
    called = {
        "configure": None,
        "run_stdio": False,
    }

    async def fake_run_stdio() -> None:
        called["run_stdio"] = True

    def fake_configure(level: str) -> None:
        called["configure"] = level

    monkeypatch.setattr(cli, "run_stdio", fake_run_stdio)
    monkeypatch.setattr(cli, "configure_logging", fake_configure)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    cli.main()

    assert called["run_stdio"] is True
    assert called["configure"] == "DEBUG"


class DummyClient:
    def __init__(self) -> None:
        self.rate_limit_remaining = 123
        self.rate_limit_reset = 456
        self.closed = False

    def close(self) -> None:
        self.closed = True


class DummyGraphQL:
    def __init__(self) -> None:
        self.rate_limit_remaining = 12
        self.rate_limit_reset = 34
        self.rate_limit_used = 5
        self.rate_limit_cost = 2
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.anyio
async def test_jsonrpc_integration_health_flow():
    client = DummyClient()
    graphql = DummyGraphQL()
    server = MCPServer(token="token", client=client, graphql=graphql)
    rpc = JSONRPCServer(server.handlers(), schemas=server.schemas())

    try:
        initialize = await rpc.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert initialize["result"]["serverInfo"]["name"] == "github-review"

        tools_list = await rpc.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = {tool["name"] for tool in tools_list["result"]["tools"]}
        assert "health" in tool_names

        health_call = await rpc.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "health", "arguments": {}},
            }
        )

        [content] = health_call["result"]["content"]
        assert content["type"] == "json"
        assert content["json"]["status"] == "ok"
        assert content["json"]["rate_limit"]["remaining"] == 123
        assert content["json"]["graphql_rate_limit"]["used"] == 5
    finally:
        await server.aclose()
        assert client.closed is True
        assert graphql.closed is True
