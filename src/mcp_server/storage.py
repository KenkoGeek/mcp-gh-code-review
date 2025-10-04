"""Persistence helpers using SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import anyio

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
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, isolation_level=None, check_same_thread=False)
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
        with self._connection() as conn:
            conn.execute(
                (
                    "REPLACE INTO review_threads(" 
                    "review_comment_id, thread_id, file, line, commit_id) "
                    "VALUES(?,?,?,?,?)"
                ),
                (review_comment_id, thread_id, file, line, commit_id),
            )

    async def get_thread(self, review_comment_id: str) -> str | None:
        return await anyio.to_thread.run_sync(self._fetch_thread, review_comment_id)

    def _fetch_thread(self, review_comment_id: str) -> str | None:
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT thread_id FROM review_threads WHERE review_comment_id = ?",
                (review_comment_id,),
            )
            row = cur.fetchone()
        return row[0] if row else None

