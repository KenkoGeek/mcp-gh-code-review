"""FastAPI webhook endpoint."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request, Response

app = FastAPI(title="MCP GitHub Review Server")


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> Response:
    secret = os.environ.get("WEBHOOK_SECRET")
    if secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=400, detail="Missing signature")
        body = await request.body()
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Signature mismatch")
    
    return Response(status_code=202)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
