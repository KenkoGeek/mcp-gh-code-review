import pytest
import respx
from httpx import Response

from mcp_server.actions import GitHubClient


@respx.mock
def test_invalid_token():
    respx.get("https://api.github.com/user").mock(
        return_value=Response(401, json={"message": "Bad credentials"})
    )

    with GitHubClient(token="invalid_token") as client:
        with pytest.raises(ValueError, match="Invalid GitHub token.*Bad credentials"):
            client.get("/user")


@respx.mock
def test_resource_not_found():
    respx.get("https://api.github.com/repos/owner/repo/pulls/999").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )

    with GitHubClient(token="test_token") as client:
        with pytest.raises(ValueError, match="Resource not found.*Not Found"):
            client.get("/repos/owner/repo/pulls/999")


@respx.mock
def test_rate_limit_exceeded():
    respx.get("https://api.github.com/user").mock(
        return_value=Response(403, json={"message": "API rate limit exceeded"})
    )

    with GitHubClient(token="test_token") as client:
        with pytest.raises(ValueError, match="rate limit exceeded"):
            client.get("/user")


@respx.mock
def test_rate_limit_429():
    respx.get("https://api.github.com/user").mock(
        return_value=Response(429, json={"message": "You have exceeded a secondary rate limit"})
    )

    with GitHubClient(token="test_token") as client:
        with pytest.raises(ValueError, match="rate limit exceeded"):
            client.get("/user")


@respx.mock
def test_connection_failed():
    import httpx
    respx.get("https://api.github.com/user").mock(
        side_effect=httpx.ConnectError("Connection error")
    )

    with GitHubClient(token="test_token") as client:
        with pytest.raises(ValueError, match="connection failed"):
            client.get("/user")
