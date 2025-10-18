from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import mcp_server.server as server_module
from mcp_server.server import MCPServer


@pytest.mark.parametrize(
    "url, expected",
    [
        ("git@github.com:owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("git@github.com:owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("git@github.com:owner/repo/extra/path.git", None),  # Invalid: extra path
        ("https://example.com/owner/repo.git", None),  # Wrong host
        ("", None),  # Empty
        ("invalid-url", None),  # Malformed
        ("git@github.com:owner", None),  # Missing repo
        ("https://github.com/owner", None),  # Missing repo
    ],
)
def test_parse_repo_from_url(url, expected):
    """Test URL parsing with edge cases."""
    result = MCPServer._parse_repo_from_url(url)
    assert result == expected


@pytest.mark.parametrize(
    "remote_url, expected",
    [
        ("git@github.com:owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("git@github.com:owner/repo", ("owner", "repo")),  # No .git suffix
        ("https://github.com/owner/repo", ("owner", "repo")),  # No .git suffix
        ("https://github.com/owner/repo/", ("owner", "repo")),  # Trailing slash
    ],
)
def test_get_repo_reads_git_config(monkeypatch, tmp_path, remote_url, expected):
    fake_repo = tmp_path / "project"
    fake_repo.mkdir()

    # Create fake source tree so Path(__file__) parent traversal reaches fake_repo
    src_dir = fake_repo / "src" / "mcp_server"
    src_dir.mkdir(parents=True)
    server_file = src_dir / "server.py"
    server_file.write_text("# stub")

    git_dir = fake_repo / ".git"
    git_dir.mkdir()
    config_path = git_dir / "config"
    config_path.write_text(f'[remote "origin"]\n\turl = {remote_url}\n')

    monkeypatch.setattr(server_module, "__file__", str(server_file))
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    def raise_file_not_found(*args, **kwargs):  # pragma: no cover - helper for clarity
        raise FileNotFoundError()

    monkeypatch.setattr(server_module.subprocess, "run", raise_file_not_found)

    server = MCPServer(token="token", client=MagicMock(), graphql=MagicMock())

    assert server._get_repo() == expected


def test_get_repo_supports_upstream_remote(monkeypatch, tmp_path):
    fake_repo = tmp_path / "project"
    fake_repo.mkdir()

    src_dir = fake_repo / "src" / "mcp_server"
    src_dir.mkdir(parents=True)
    server_file = src_dir / "server.py"
    server_file.write_text("# stub")

    git_dir = fake_repo / ".git"
    git_dir.mkdir()
    config_path = git_dir / "config"
    config_path.write_text('[remote "upstream"]\n\turl = https://github.com/example/demo.git\n')

    monkeypatch.setattr(server_module, "__file__", str(server_file))
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    def raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(server_module.subprocess, "run", raise_file_not_found)

    server = MCPServer(token="token", client=MagicMock(), graphql=MagicMock())

    assert server._get_repo() == ("example", "demo")


def test_get_repo_falls_back_to_remote_v(monkeypatch, tmp_path):
    fake_repo = tmp_path / "project"
    fake_repo.mkdir()

    src_dir = fake_repo / "src" / "mcp_server"
    src_dir.mkdir(parents=True)
    server_file = src_dir / "server.py"
    server_file.write_text("# stub")

    git_dir = fake_repo / ".git"
    git_dir.mkdir()

    monkeypatch.setattr(server_module, "__file__", str(server_file))
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    class DummyCompletedProcess:
        def __init__(self, returncode: int, stdout: str = ""):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(cmd, cwd=None, capture_output=None, text=None, timeout=None):
        if cmd[:3] == ["git", "remote", "get-url"]:
            return DummyCompletedProcess(returncode=1)
        if cmd == ["git", "remote", "-v"]:
            stdout = (
                "origin https://github.com/sample/project.git (fetch)\n"
                "origin https://github.com/sample/project.git (push)\n"
            )
            return DummyCompletedProcess(returncode=0, stdout=stdout)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(server_module.subprocess, "run", fake_run)

    server = MCPServer(token="token", client=MagicMock(), graphql=MagicMock())

    assert server._get_repo() == ("sample", "project")
