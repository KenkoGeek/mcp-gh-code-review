from mcp_server.bot_detector import is_bot


def test_bot_detection():
    assert is_bot("dependabot[bot]") is True
    assert is_bot("renovate[bot]") is True
    assert is_bot("github-actions[bot]") is True
    assert is_bot("codecov-bot") is True
    assert is_bot("alice") is False
    assert is_bot("john-doe") is False
