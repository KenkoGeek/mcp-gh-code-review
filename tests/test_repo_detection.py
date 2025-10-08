from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import mcp_server.server as server_module
from mcp_server.server import MCPServer


@pytest.mark.parametrize(
    "remote_url, expected",
    [
        ("git@github.com:owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
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
