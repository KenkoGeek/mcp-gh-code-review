"""Schemas for context management tools."""

from __future__ import annotations

from pydantic import BaseModel


class SetContextRequest(BaseModel):
    owner: str | None = None
    repo: str | None = None
    pr_number: int | None = None
    branch: str | None = None


class GetContextRequest(BaseModel):
    pass


class DetectRepoRequest(BaseModel):
    path: str = "."


class FetchPRInfoRequest(BaseModel):
    pr_number: int


class GetPRDataRequest(BaseModel):
    pr_number: int
    include: list[str] | None = None  # ["info", "reviews", "comments", "inline_comments"]


class AnalyzePRReviewsRequest(BaseModel):
    pr_number: int


__all__ = [
    "FetchPRInfoRequest",
    "GetPRDataRequest",
    "AnalyzePRReviewsRequest",
]