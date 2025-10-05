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
    schemas: dict[str, dict[str, Any]] | None = None

    async def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        if "method" not in message:
            raise ValueError("Invalid JSON-RPC request")
        method = message["method"]
        
        # Handle MCP protocol methods
        match method:
            case "initialize":
                return await self._handle_initialize(message)
            case "tools/list":
                return await self._handle_tools_list(message)
            case "tools/call":
                return await self._handle_tools_call(message)
        
        handler = self.handlers.get(method)
        if handler is None:
            raise ValueError(f"Unknown method: {method}")
        params = message.get("params", {})
        result = await handler(params)
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": result}
    
    async def _handle_initialize(self, message: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "github-review", "version": "0.1.0"}
            }
        }
    
    async def _handle_tools_list(self, message: dict[str, Any]) -> dict[str, Any]:
        tools = []
        for name, _handler in self.handlers.items():
            tool: dict[str, Any] = {"name": name, "description": f"MCP tool: {name}"}
            if self.schemas and name in self.schemas:
                tool["inputSchema"] = self.schemas[name]
            else:
                tool["inputSchema"] = {"type": "object", "properties": {}}
            tools.append(tool)
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"tools": tools}}
    
    async def _handle_tools_call(self, message: dict[str, Any]) -> dict[str, Any]:
        params = message.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name not in self.handlers:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        result = await self.handlers[tool_name](tool_args)
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"content": [{"type": "text", "text": str(result)}]}
        }

    async def serve_stdio(self) -> None:
        import sys
        while True:
            try:
                line = await anyio.to_thread.run_sync(sys.stdin.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                message = json.loads(line)
                response = await self.handle(message)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except (EOFError, KeyboardInterrupt):
                break
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id") if "message" in locals() else None,
                    "error": {"code": -32603, "message": str(e)}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

