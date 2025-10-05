import pytest
from mcp_server.server import MCPServer
from mcp_server.actions import GitHubClient
from mcp_server.graphql_client import GitHubGraphQLClient


@pytest.mark.anyio
async def test_health_tool():
    client = GitHubClient(token="test_token")
    graphql = GitHubGraphQLClient(token="test_token")
    server = MCPServer(token="test_token", client=client, graphql=graphql)
    result = await server.health({})
    assert result["status"] == "ok"
    assert "rate_limit" in result
