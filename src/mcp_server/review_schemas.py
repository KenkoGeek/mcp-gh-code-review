"""Schemas for orchestrated PR review."""

from pydantic import BaseModel


class ReviewPRRequest(BaseModel):
    pr_number: int
    include_all: bool = True


__all__ = ["ReviewPRRequest"]