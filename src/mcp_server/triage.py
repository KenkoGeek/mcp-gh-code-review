"""Triage logic for PR events."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from .classifier import ActorClassifier
from .config import PolicyConfig
from .schemas import (
    Action,
    ActionType,
    BaseEvent,
    CommentEvent,
    ReviewEvent,
    ReviewState,
    StatusEvent,
    StatusState,
    TriagedActions,
)

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class TriageEngine:
    """Decide which actions should be taken for a GitHub event."""

    classifier: ActorClassifier
    policy: PolicyConfig

    def triage(self, event: BaseEvent | ReviewEvent | CommentEvent | StatusEvent) -> TriagedActions:
        classification = self.classifier.classify(
            event.actor_login, name=getattr(event, "actor_name", None)
        )
        logger.info("triaging_event", event_id=event.event_id, actor=event.actor_login, actor_type=classification.actor_type)
        triaged = TriagedActions()
        if isinstance(event, ReviewEvent):
            self._handle_review(event, triaged)
        if isinstance(event, CommentEvent):
            self._handle_comment(event, classification.actor_type, triaged)
        if isinstance(event, StatusEvent):
            self._handle_status(event, triaged)
        return triaged

    def _handle_review(self, event: ReviewEvent, triaged: TriagedActions) -> None:
        if event.state == ReviewState.changes_requested:
            triaged.actions.append(
                Action(
                    type=ActionType.comment,
                    value="Thanks for the thorough review! We'll address these changes.",
                    metadata={"event_id": event.event_id},
                )
            )
            triaged.labels.append("needs-changes")
        elif event.state == ReviewState.approved:
            triaged.labels.append("approved")

    def _handle_comment(
        self, event: CommentEvent, actor_type: str, triaged: TriagedActions
    ) -> None:
        pr_metadata = {"owner": event.pr.owner, "repo": event.pr.repo, "number": event.pr.number}
        if actor_type == "bot":
            triaged.actions.append(
                Action(
                    type=ActionType.comment,
                    value="🤖 Automated feedback noted. Running follow-up automation if required.",
                    metadata={"event_id": event.event_id, "comment_id": event.comment_id, "pr": pr_metadata},
                )
            )
        else:
            triaged.actions.append(
                Action(
                    type=ActionType.comment,
                    value="Thanks for the feedback! We'll take a look right away.",
                    metadata={"event_id": event.event_id, "comment_id": event.comment_id, "pr": pr_metadata},
                )
            )
        if event.path:
            for prefix, labels in self.policy.labels.items():
                if event.path.startswith(prefix):
                    triaged.labels.extend(label for label in labels if label not in triaged.labels)

    def _handle_status(self, event: StatusEvent, triaged: TriagedActions) -> None:
        if event.state == StatusState.failure:
            triaged.labels.append("ci-failed")
            triaged.actions.append(
                Action(type=ActionType.rerun_checks, metadata={"context": event.context})
            )
        elif event.state == StatusState.success:
            triaged.labels.append("ci-passed")

