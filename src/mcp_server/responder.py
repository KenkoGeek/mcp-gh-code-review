"""Response generation depending on actor type."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from .schemas import Action, ActionType, GenerateReplyRequest, GenerateReplyResponse

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class Responder:
    """Generate replies for comments and review threads."""

    def generate(self, request: GenerateReplyRequest) -> GenerateReplyResponse:
        logger.info("generating_reply", actor_type=request.actor_type.value, thread_id=request.thread.id)
        if request.actor_type.value == "bot":
            body = self._bot_reply(request)
            followups = [
                Action(
                    type=ActionType.comment,
                    value="Bot response tracked",
                    metadata={"thread": request.thread.id},
                )
            ]
            return GenerateReplyResponse(body=body, followups=followups, resolve_thread=False)
        body = self._human_reply(request)
        followups: list[Action] = []
        if request.code_context and request.code_context.after:
            followups.append(
                Action(
                    type=ActionType.comment,
                    value=f"Proposed change:\n```diff\n{request.code_context.after}\n```",
                    metadata={"thread": request.thread.id},
                )
            )
        return GenerateReplyResponse(body=body, resolve_thread=False, followups=followups)

    def _bot_reply(self, request: GenerateReplyRequest) -> str:
        base = "🤖 Thanks for the automated update."
        if request.code_context:
            base += " We'll verify the suggested changes against policy."
        return base

    def _human_reply(self, request: GenerateReplyRequest) -> str:
        intro = "Thanks for taking the time to review this change."
        details = request.comment.strip().splitlines()
        summary = details[0] if details else ""
        parts = [intro]
        if summary:
            parts.append(f"You mentioned: \"{summary}\"")
        if request.thread.file and request.thread.line:
            parts.append(
                "We'll revisit "
                f"`{request.thread.file}` line {request.thread.line} and follow up shortly."
            )
        return " ".join(parts)


__all__ = ["Responder"]
