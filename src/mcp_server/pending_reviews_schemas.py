"""Schemas for pending reviews tool."""

from __future__ import annotations

from pydantic import BaseModel


class SubmitPendingReviewRequest(BaseModel):
    """Request to submit pending review."""
    pr_number: int
    review_id: str
    event: str  # APPROVE, REQUEST_CHANGES, COMMENT
    body: str = ""


class PendingReviewsResponse(BaseModel):
    """Response with pending reviews data."""
    pending_reviews: list[dict]
    count: int
    has_comments: bool
    error: str | None = None


class SubmitReviewResponse(BaseModel):
    """Response after submitting review."""
    success: bool
    review: dict | None = None
    error: str | None = None


__all__ = [
    "SubmitPendingReviewRequest", 
    "PendingReviewsResponse",
    "SubmitReviewResponse"
]