"""Smart reply tool that automatically determines correct GitHub comment type."""

from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionExecutor
from .comment_classifier import CommentClassifier, CommentType
from .schemas import Action, ActionResult, ActionType


@dataclass(slots=True)
class SmartReply:
    """Automatically determine correct GitHub comment type and respond appropriately."""
    
    action_executor: ActionExecutor
    comment_classifier: CommentClassifier
    
    def reply_to_comment(
        self, 
        pr_number: int, 
        comment_id: str, 
        reply_text: str,
        path: str | None = None,
        line: int | None = None,
        diff_hunk: str | None = None
    ) -> ActionResult:
        """Smart reply that automatically determines correct comment type."""
        
        # Build comment data for classification
        comment_data = {
            "id": comment_id,
            "path": path,
            "line": line,
            "diff_hunk": diff_hunk,
            "in_reply_to_id": comment_id  # This is a reply
        }
        
        # Classify the comment type
        metadata = self.comment_classifier.classify_comment(comment_data, pr_number)
        
        # Create appropriate action based on classification
        if metadata.comment_type == CommentType.REVIEW_COMMENT_REPLY:
            # Inline comment reply
            action = Action(
                type=ActionType.add_review_comment,
                value=reply_text,
                metadata={
                    "pr_number": pr_number,
                    "in_reply_to": comment_id
                }
            )
        else:
            # General comment reply
            action = Action(
                type=ActionType.comment,
                value=reply_text,
                metadata={
                    "pr_number": pr_number,
                    "in_reply_to": comment_id
                }
            )
        
        # Execute the action
        results = self.action_executor.apply([action])
        return results[0] if results else ActionResult(
            action=action, 
            success=False, 
            detail="No results returned"
        )


__all__ = ["SmartReply"]