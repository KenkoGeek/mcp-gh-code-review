from pathlib import Path

import pytest

from mcp_server.schemas import MapInlineThreadRequest
from mcp_server.storage import Storage
from mcp_server.thread_manager import ThreadManager


@pytest.mark.anyio
async def test_thread_mapping(tmp_path: Path):
    storage = Storage(tmp_path / "threads.db")
    manager = ThreadManager(storage=storage)
    request = MapInlineThreadRequest(
        review_comment_id="123",
        file="src/app.py",
        line=5,
        commit_id="abc",
    )
    response = await manager.map_thread(request)
    assert response.thread_id.startswith("thread-")
    response2 = await manager.map_thread(request)
    assert response2.thread_id == response.thread_id
