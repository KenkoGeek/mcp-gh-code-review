"""Pydantic models for MCP tools."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class ActorType(str, Enum):
    bot = "bot"
    human = "human"


class ClassificationResult(BaseModel):
    actor_type: ActorType
    reason: str
    matched_rule: str | None = None


class ClassifyActorRequest(BaseModel):
    login: str
    name: str | None = None


class ThreadContext(BaseModel):
    id: str
    file: str | None = None
    line: int | None = None


class CodeContext(BaseModel):
    path: str
    before: str | None = None
    after: str | None = None


class ActionType(str, Enum):
    apply_label = "apply_label"
    remove_label = "remove_label"
    assign = "assign"
    unassign = "unassign"
    request_review = "request_review"
    comment = "comment"
    rerun_checks = "rerun_checks"
    open_issue = "open_issue"
    resolve_thread = "resolve_thread"
    submit_review = "submit_review"
    dismiss_review = "dismiss_review"
    add_review_comment = "add_review_comment"
    reply_to_pending_review = "reply_to_pending_review"


class Action(BaseModel):
    type: ActionType
    value: str | None = None
    metadata: dict = Field(default_factory=dict)


class ActionResult(BaseModel):
    action: Action
    success: bool
    detail: str | None = None


class PullRequestRef(BaseModel):
    owner: str
    repo: str
    number: int


class BaseEvent(BaseModel):
    pr: PullRequestRef
    actor_login: str
    actor_name: str | None = None
    event_id: str
    delivery_id: str | None = None


class ReviewState(str, Enum):
    approved = "APPROVED"
    changes_requested = "CHANGES_REQUESTED"
    comment = "COMMENTED"


class ReviewEvent(BaseEvent):
    state: ReviewState
    body: str | None = None


class CommentEvent(BaseEvent):
    comment_id: str
    body: str
    path: str | None = None
    line: int | None = None
    in_reply_to: str | None = None


class StatusState(str, Enum):
    success = "success"
    failure = "failure"
    pending = "pending"


class StatusEvent(BaseEvent):
    state: StatusState
    context: str
    target_url: HttpUrl | None = None


class TriagedActions(BaseModel):
    actions: list[Action] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    assignments: list[str] = Field(default_factory=list)


class TriageEventRequest(BaseModel):
    event: CommentEvent | ReviewEvent | StatusEvent | BaseEvent
    policy: dict | None = None


class GenerateReplyRequest(BaseModel):
    actor_type: ActorType
    thread: ThreadContext
    comment: str
    code_context: CodeContext | None = None


class GenerateReplyResponse(BaseModel):
    body: str
    resolve_thread: bool = False
    followups: list[Action] = Field(default_factory=list)


class ApplyActionsRequest(BaseModel):
    actions: Sequence[Action]
    dry_run: bool = False


class ApplyActionsResponse(BaseModel):
    results: list[ActionResult]


class MapInlineThreadRequest(BaseModel):
    review_comment_id: str
    file: str
    line: int
    commit_id: str | None = None


class MapInlineThreadResponse(BaseModel):
    thread_id: str


class SetPolicyRequest(BaseModel):
    policy: dict


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    database_healthy: bool = True
    rate_limit: dict = Field(default_factory=dict)


class ManagePendingReviewRequest(BaseModel):
    pr_number: int
    action: str  # "submit", "dismiss", "add_comment"
    event: str = "COMMENT"  # "APPROVE", "REQUEST_CHANGES", "COMMENT"
    body: str | None = None
    comments: list[dict] | None = None  # For adding review comments


class ManagePendingReviewResponse(BaseModel):
    success: bool
    review_id: int | None = None
    message: str | None = None


def schema_for(model: type[BaseModel]) -> dict:
    """Return JSON schema for a model."""

    return model.model_json_schema()


__all__ = [
    "ActorType",
    "ClassificationResult",
    "ClassifyActorRequest",
    "ThreadContext",
    "CodeContext",
    "ActionType",
    "Action",
    "ActionResult",
    "PullRequestRef",
    "BaseEvent",
    "ReviewEvent",
    "CommentEvent",
    "StatusEvent",
    "TriagedActions",
    "TriageEventRequest",
    "GenerateReplyRequest",
    "GenerateReplyResponse",
    "ApplyActionsRequest",
    "ApplyActionsResponse",
    "MapInlineThreadRequest",
    "MapInlineThreadResponse",
    "SetPolicyRequest",
    "HealthResponse",
    "ManagePendingReviewRequest",
    "ManagePendingReviewResponse",
    "schema_for",
]
