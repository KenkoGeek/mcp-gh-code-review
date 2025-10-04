"""Thread management helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import MapInlineThreadRequest, MapInlineThreadResponse
from .storage import Storage


@dataclass(slots=True)
class ThreadManager:
    storage: Storage

    async def map_thread(self, request: MapInlineThreadRequest) -> MapInlineThreadResponse:
        existing = await self.storage.get_thread(request.review_comment_id)
        if existing:
            return MapInlineThreadResponse(thread_id=existing)
        generated = f"thread-{request.review_comment_id}"
        await self.storage.map_thread(
            request.review_comment_id, generated, request.file, request.line, request.commit_id
        )
        return MapInlineThreadResponse(thread_id=generated)


__all__ = ["ThreadManager"]
