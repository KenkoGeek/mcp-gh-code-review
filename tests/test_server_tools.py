import pytest

from mcp_server.config import ServerConfig
from mcp_server.server import MCPServer


@pytest.fixture
def server_config(tmp_path):
    return ServerConfig(bot_actors=["bot"], policy_path=None)


@pytest.mark.anyio
async def test_classify_actor_tool(server_config):
    server = MCPServer.create(server_config)
    result = await server.classify_actor({"login": "dependabot[bot]"})
    assert result["actor_type"] == "bot"


@pytest.mark.anyio
async def test_generate_reply_tool(server_config):
    server = MCPServer.create(server_config)
    response = await server.generate_reply(
        {
            "actor_type": "human",
            "thread": {"id": "t1", "file": "src/app.py", "line": 12},
            "comment": "Looks good",
        }
    )
    assert "Thanks" in response["body"]


@pytest.mark.anyio
async def test_triage_event_tool(server_config):
    server = MCPServer.create(server_config)
    response = await server.triage_event(
        {
            "event": {
                "pr": {"owner": "acme", "repo": "demo", "number": 1},
                "actor_login": "bob",
                "event_id": "evt-1",
                "comment_id": "c-1",
                "body": "ping",
                "path": "src/main.py",
                "line": 1,
            }
        }
    )
    assert response["actions"]
