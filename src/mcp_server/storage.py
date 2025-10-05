"""Persistence helpers using SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import anyio
import structlog

logger = structlog.get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS review_threads (
    review_comment_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    file TEXT,
    line INTEGER,
    commit_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Storage:
    def __init__(self, path: Path) -> None:
        self._path = path
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as conn:
                conn.executescript(SCHEMA)
            logger.info("storage_initialized", path=str(path))
        except (OSError, sqlite3.Error) as exc:
            logger.error("storage_init_failed", path=str(path), error=str(exc))
            raise RuntimeError(f"Failed to initialize storage at {path}: {exc}") from exc

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, isolation_level=None, check_same_thread=False, timeout=5.0)
        try:
            yield conn
        finally:
            conn.close()

    async def map_thread(
        self,
        review_comment_id: str,
        thread_id: str,
        file: str,
        line: int,
        commit_id: str | None,
    ) -> None:
        await anyio.to_thread.run_sync(
            self._insert_or_replace, review_comment_id, thread_id, file, line, commit_id
        )

    def _insert_or_replace(
        self,
        review_comment_id: str,
        thread_id: str,
        file: str,
        line: int,
        commit_id: str | None,
    ) -> None:
        try:
            with self._connection() as conn:
                conn.execute(
                    (
                        "REPLACE INTO review_threads(" 
                        "review_comment_id, thread_id, file, line, commit_id) "
                        "VALUES(?,?,?,?,?)"
                    ),
                    (review_comment_id, thread_id, file, line, commit_id),
                )
            logger.debug("thread_mapped", review_comment_id=review_comment_id, thread_id=thread_id)
        except sqlite3.Error as exc:
            logger.error("thread_map_failed", review_comment_id=review_comment_id, error=str(exc))
            raise RuntimeError(f"Failed to map thread: {exc}") from exc

    async def get_thread(self, review_comment_id: str) -> str | None:
        return await anyio.to_thread.run_sync(self._fetch_thread, review_comment_id)

    def _fetch_thread(self, review_comment_id: str) -> str | None:
        try:
            with self._connection() as conn:
                cur = conn.execute(
                    "SELECT thread_id FROM review_threads WHERE review_comment_id = ?",
                    (review_comment_id,),
                )
                row = cur.fetchone()
            return row[0] if row else None
        except sqlite3.Error as exc:
            logger.error("thread_fetch_failed", review_comment_id=review_comment_id, error=str(exc))
            raise RuntimeError(f"Failed to fetch thread: {exc}") from exc

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self._connection() as conn:
                conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

