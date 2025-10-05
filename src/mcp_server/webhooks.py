"""FastAPI application exposing GitHub webhook endpoint."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response

from .config import load_from_env
from .server import MCPServer

logger = logging.getLogger(__name__)
app = FastAPI(title="MCP GitHub Review Server")


def get_server() -> MCPServer:
    config = load_from_env(os.environ)
    return MCPServer.create(config)


async def verify_signature(request: Request, signature: str | None, secret: str | None) -> None:
    if secret is None:
        return
    if signature is None:
        raise HTTPException(status_code=400, detail="Missing signature")
    body = await request.body()
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Signature mismatch")


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    server: MCPServer = Depends(get_server),  # noqa: B008 - FastAPI dependency injection
) -> Response:
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    await verify_signature(request, x_hub_signature_256, secret)
    payload = await request.json()
    logger.info(f"webhook.received event={x_github_event} delivery={payload.get('delivery')}")
    # For now we simply acknowledge receipt; orchestration happens asynchronously.
    return Response(status_code=202)


@app.get("/healthz")
async def health() -> dict[str, Any]:
    return {"status": "ok"}
