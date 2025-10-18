"""FastAPI webhook endpoint."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError

app = FastAPI(title="MCP GitHub Review Server")


class BaseWebhookPayload(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)


class PullRequestPayload(BaseWebhookPayload):
    pull_request: dict[str, Any]


class IssueCommentPayload(BaseWebhookPayload):
    issue: dict[str, Any]
    comment: dict[str, Any]


class PullRequestReviewPayload(BaseWebhookPayload):
    pull_request: dict[str, Any]
    review: dict[str, Any]


class PullRequestReviewCommentPayload(BaseWebhookPayload):
    pull_request: dict[str, Any]
    comment: dict[str, Any]


EVENT_SCHEMAS: dict[str, type[BaseWebhookPayload]] = {
    "pull_request": PullRequestPayload,
    "pull_request_review": PullRequestReviewPayload,
    "pull_request_review_comment": PullRequestReviewCommentPayload,
    "issue_comment": IssueCommentPayload,
}


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from None

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload: expected JSON object")

    if not x_github_event:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    schema = EVENT_SCHEMAS.get(x_github_event, BaseWebhookPayload)

    try:
        schema.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc.errors()}") from None

    return Response(status_code=202)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
