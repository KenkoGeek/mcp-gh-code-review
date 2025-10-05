import respx
from httpx import Response

from mcp_server.actions import GitHubClient


@respx.mock
def test_github_client_post():
    client = GitHubClient(token="test_token")
    route = respx.post("https://api.github.com/repos/acme/demo/issues/1/labels").mock(
        return_value=Response(200, json={"labels": []})
    )
    response = client.post("/repos/acme/demo/issues/1/labels", payload={"labels": ["bug"]})
    assert response.status_code == 200
    assert route.called
