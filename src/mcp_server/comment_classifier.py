"""GitHub comment type classification for accurate response routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommentType(Enum):
    """GitHub comment types with specific API requirements."""
    ISSUE_COMMENT = "issue_comment"           # General PR discussion
    REVIEW_COMMENT = "review_comment"         # Inline code comment
    REVIEW_COMMENT_REPLY = "review_reply"     # Reply to inline comment
    PULL_REQUEST_REVIEW = "pr_review"         # Overall PR review
    PENDING_REVIEW_COMMENT = "pending_comment" # Pending inline comment
    SUGGESTION_COMMENT = "suggestion"         # Code suggestion


@dataclass(slots=True)
class CommentMetadata:
    """Metadata required for different comment types."""
    comment_type: CommentType
    pr_number: int
    comment_id: str | None = None
    path: str | None = None
    line: int | None = None
    commit_id: str | None = None
    in_reply_to: str | None = None
    requires_commit_id: bool = False


class CommentClassifier:
    """Classify GitHub comments to determine correct API endpoint and parameters."""
    
    def classify_comment(self, comment_data: dict[str, Any], pr_number: int) -> CommentMetadata:
        """Classify comment and return required metadata for API calls."""
        
        # Check for inline comment indicators
        has_path = bool(comment_data.get("path"))
        has_line = bool(comment_data.get("line") or comment_data.get("original_line"))
        has_diff_hunk = bool(comment_data.get("diff_hunk"))
        is_reply = bool(comment_data.get("in_reply_to_id"))
        
        # Determine comment type
        if has_path and has_line and has_diff_hunk:
            if is_reply:
                comment_type = CommentType.REVIEW_COMMENT_REPLY
            else:
                comment_type = CommentType.REVIEW_COMMENT
        elif is_reply:
            # Reply to general comment
            comment_type = CommentType.ISSUE_COMMENT
        else:
            # General PR comment
            comment_type = CommentType.ISSUE_COMMENT
        
        return CommentMetadata(
            comment_type=comment_type,
            pr_number=pr_number,
            comment_id=str(comment_data.get("id", "")),
            path=comment_data.get("path"),
            line=comment_data.get("line") or comment_data.get("original_line"),
            commit_id=comment_data.get("commit_id"),
            in_reply_to=str(comment_data.get("in_reply_to_id", "")) if is_reply else None,
            requires_commit_id=(comment_type == CommentType.REVIEW_COMMENT and not is_reply)
        )
    
    def get_api_endpoint(self, metadata: CommentMetadata) -> str:
        """Get correct GitHub API endpoint for comment type."""
        match metadata.comment_type:
            case CommentType.ISSUE_COMMENT:
                return f"/repos/{{owner}}/{{repo}}/issues/{metadata.pr_number}/comments"
            case CommentType.REVIEW_COMMENT | CommentType.REVIEW_COMMENT_REPLY:
                return f"/repos/{{owner}}/{{repo}}/pulls/{metadata.pr_number}/comments"
            case _:
                return f"/repos/{{owner}}/{{repo}}/issues/{metadata.pr_number}/comments"
    
    def get_request_payload(self, metadata: CommentMetadata, body: str) -> dict[str, Any]:
        """Build API request payload based on comment type."""
        payload = {"body": body}
        
        match metadata.comment_type:
            case CommentType.REVIEW_COMMENT:
                # New inline comment - requires path, line, commit_id
                payload.update({
                    "path": metadata.path,
                    "line": metadata.line,
                    "commit_sha": metadata.commit_id  # Will be auto-detected if None
                })
            case CommentType.REVIEW_COMMENT_REPLY:
                # Reply to inline comment - requires in_reply_to
                payload["in_reply_to"] = int(metadata.in_reply_to)
            case CommentType.ISSUE_COMMENT:
                # General comment or reply - no extra fields needed
                pass
        
        return payload
    
    def validate_metadata(self, metadata: CommentMetadata) -> list[str]:
        """Validate that metadata has required fields for comment type."""
        errors = []
        
        match metadata.comment_type:
            case CommentType.REVIEW_COMMENT:
                if not metadata.path:
                    errors.append("path required for inline comments")
                if not metadata.line:
                    errors.append("line required for inline comments")
                # commit_id will be auto-detected if missing
            case CommentType.REVIEW_COMMENT_REPLY:
                if not metadata.in_reply_to:
                    errors.append("in_reply_to required for comment replies")
        
        return errors


__all__ = ["CommentClassifier", "CommentType", "CommentMetadata"]