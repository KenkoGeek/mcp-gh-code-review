import pytest

from mcp_server.actions import GitHubClient
from mcp_server.graphql_client import GitHubGraphQLClient
from mcp_server.server import MCPServer


@pytest.mark.anyio
async def test_health_tool():
    client = GitHubClient(token="test_token")
    graphql = GitHubGraphQLClient(token="test_token")
    server = MCPServer(token="test_token", client=client, graphql=graphql)
    try:
        result = await server.health({})
        assert result["status"] == "ok"
        assert "rate_limit" in result
        assert "graphql_rate_limit" in result
    finally:
        await server.aclose()
