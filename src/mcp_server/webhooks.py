"""FastAPI webhook endpoint."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

app = FastAPI(title="MCP GitHub Review Server")


class WebhookPayload(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)
    pull_request: dict | None = None
    issue: dict | None = None
    comment: dict | None = None
    review: dict | None = None


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> Response:
    body = await request.body()
    secret = os.environ.get("WEBHOOK_SECRET")
    if secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=400, detail="Missing signature")
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Signature mismatch")
    
    try:
        payload = await request.json()
        WebhookPayload(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from None
    
    return Response(status_code=202)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
