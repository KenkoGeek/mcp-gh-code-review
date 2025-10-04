import respx
from httpx import Response

from mcp_server.actions import ActionExecutor, GitHubClient
from mcp_server.config import GitHubConfig
from mcp_server.schemas import Action, ActionType


def test_apply_actions_dry_run():
    executor = ActionExecutor(client=GitHubClient(config=GitHubConfig(token="x")))
    actions = [Action(type=ActionType.apply_label, value="needs-review", metadata={})]
    results = executor.apply(actions, dry_run=True)
    assert results[0].detail == "dry-run"


@respx.mock
def test_apply_label_hits_github():
    config = GitHubConfig(token="token")
    executor = ActionExecutor(client=GitHubClient(config=config))
    route = respx.post("https://api.github.com/repos/acme/demo/issues/1/labels").mock(
        return_value=Response(200, json={"labels": []})
    )
    action = Action(
        type=ActionType.apply_label,
        value="needs-review",
        metadata={"pr": {"owner": "acme", "repo": "demo", "number": 1}},
    )
    results = executor.apply([action])
    assert results[0].success
    assert route.called
