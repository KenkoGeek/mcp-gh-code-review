"""Minimal JSON-RPC 2.0 transport for MCP tools."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import anyio

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class JSONRPCServer:
    handlers: dict[str, Handler]

    async def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        if "method" not in message:
            raise ValueError("Invalid JSON-RPC request")
        method = message["method"]
        handler = self.handlers.get(method)
        if handler is None:
            raise ValueError(f"Unknown method: {method}")
        params = message.get("params", {})
        result = await handler(params)
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": result}

    async def serve_stdio(self) -> None:
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._read_loop)

    async def _read_loop(self) -> None:
        while True:
            raw = await anyio.to_thread.run_sync(input)
            if not raw:
                continue
            message = json.loads(raw)
            response = await self.handle(message)
            print(json.dumps(response), flush=True)

