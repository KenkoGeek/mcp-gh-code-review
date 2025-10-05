"""Apply actions to GitHub."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import GitHubConfig
from .schemas import Action, ActionResult, ActionType

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class GitHubClient:
    config: GitHubConfig
    base_url: str = "https://api.github.com"
    _client: httpx.Client = field(init=False, repr=False)
    rate_limit_remaining: int = field(default=5000, init=False)
    rate_limit_reset: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._client = httpx.Client(timeout=10.0, headers=self._headers())

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        return headers

    def _update_rate_limits(self, response: httpx.Response) -> None:
        if "X-RateLimit-Remaining" in response.headers:
            self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in response.headers:
            self.rate_limit_reset = int(response.headers["X-RateLimit-Reset"])
        logger.debug(
            "rate_limit_updated", 
            remaining=self.rate_limit_remaining, 
            reset=self.rate_limit_reset
        )

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def post(self, path: str, payload: dict | None = None) -> httpx.Response:
        response = self._client.post(f"{self.base_url}{path}", json=payload)
        self._update_rate_limits(response)
        response.raise_for_status()
        return response

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def patch(self, path: str, payload: dict | None = None) -> httpx.Response:
        response = self._client.patch(f"{self.base_url}{path}", json=payload)
        self._update_rate_limits(response)
        response.raise_for_status()
        return response

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def get(self, path: str) -> httpx.Response:
        response = self._client.get(f"{self.base_url}{path}")
        self._update_rate_limits(response)
        response.raise_for_status()
        return response

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def put(self, path: str, payload: dict | None = None) -> httpx.Response:
        response = self._client.put(f"{self.base_url}{path}", json=payload)
        self._update_rate_limits(response)
        response.raise_for_status()
        return response

    def close(self) -> None:
        self._client.close()


@dataclass(slots=True)
class ActionExecutor:
    client: GitHubClient
    
    def _validate_pr_metadata(self, pr: dict) -> bool:
        """Validate PR metadata to prevent path traversal."""
        required_fields = ['owner', 'repo', 'number']
        if not all(field in pr for field in required_fields):
            return False
        
        # Validate owner and repo are safe strings
        import re
        safe_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
        if not safe_pattern.match(str(pr['owner'])) or not safe_pattern.match(str(pr['repo'])):
            return False
        
        # Validate number is positive integer
        try:
            num = int(pr['number'])
            return num > 0
        except (ValueError, TypeError):
            return False

    def apply(self, actions: Iterable[Action], dry_run: bool = False) -> list[ActionResult]:
        results: list[ActionResult] = []
        for action in actions:
            if dry_run:
                results.append(ActionResult(action=action, success=True, detail="dry-run"))
                continue
            try:
                self._apply_action(action)
                results.append(ActionResult(action=action, success=True))
            except httpx.HTTPError as exc:  # pragma: no cover - network errors
                results.append(ActionResult(action=action, success=False, detail=str(exc)))
        return results

    def _apply_action(self, action: Action) -> None:
        logger.info("applying_action", action_type=action.type.value)
        if action.type == ActionType.apply_label and action.metadata:
            pr = action.metadata.get("pr")
            if pr and self._validate_pr_metadata(pr):
                path = f"/repos/{pr['owner']}/{pr['repo']}/issues/{pr['number']}/labels"
                self.client.post(path, payload={"labels": [action.value]})
        elif action.type == ActionType.comment and action.metadata:
            pr = action.metadata.get("pr")
            if pr and self._validate_pr_metadata(pr):
                payload = {"body": action.value}
                # Check if this is a reply to an inline comment
                if "in_reply_to" in action.metadata:
                    # Reply to inline comment (review comment)
                    path = f"/repos/{pr['owner']}/{pr['repo']}/pulls/{pr['number']}/comments"
                    payload["in_reply_to"] = str(action.metadata["in_reply_to"])
                else:
                    # General PR comment
                    path = f"/repos/{pr['owner']}/{pr['repo']}/issues/{pr['number']}/comments"
                self.client.post(path, payload=payload)
        elif action.type == ActionType.add_review_comment and action.metadata:
            pr = action.metadata.get("pr")
            if pr:
                # Add comment to pending review or create new review
                path = f"/repos/{pr['owner']}/{pr['repo']}/pulls/{pr['number']}/comments"
                payload = {
                    "body": action.value,
                    "commit_id": action.metadata.get("commit_id"),
                    "path": action.metadata.get("path"),
                    "line": action.metadata.get("line")
                }
                if "in_reply_to" in action.metadata:
                    payload["in_reply_to"] = str(action.metadata["in_reply_to"])
                self.client.post(path, payload=payload)
        elif action.type == ActionType.reply_to_pending_review and action.metadata:
            pr = action.metadata.get("pr")
            if pr:
                # For pending reviews, we need to submit the entire review with the reply
                # First, get the pending review
                reviews_path = f"/repos/{pr['owner']}/{pr['repo']}/pulls/{pr['number']}/reviews"
                reviews_response = self.client.get(reviews_path)
                reviews = reviews_response.json()
                
                pending_review = next((r for r in reviews if r["state"] == "PENDING"), None)
                if pending_review:
                    # Submit the pending review with our reply as a comment
                    submit_path = (
                        f"/repos/{pr['owner']}/{pr['repo']}/pulls/{pr['number']}/"
                        f"reviews/{pending_review['id']}/events"
                    )
                    payload = {
                        "event": "COMMENT",
                        "body": action.value
                    }
                    self.client.post(submit_path, payload=payload)
                else:
                    # No pending review, create a regular comment
                    path = f"/repos/{pr['owner']}/{pr['repo']}/issues/{pr['number']}/comments"
                    payload = {"body": action.value}
                    self.client.post(path, payload=payload)
        elif action.type == ActionType.submit_review and action.metadata:
            pr = action.metadata.get("pr")
            if pr:
                # Submit pending review
                path = f"/repos/{pr['owner']}/{pr['repo']}/pulls/{pr['number']}/reviews"
                payload = {
                    "event": action.metadata.get("event", "COMMENT"),
                    "body": action.value or ""
                }
                self.client.post(path, payload=payload)
        elif action.type == ActionType.dismiss_review and action.metadata:
            pr = action.metadata.get("pr")
            review_id = action.metadata.get("review_id")
            if pr and review_id:
                # Dismiss a review
                path = (
                    f"/repos/{pr['owner']}/{pr['repo']}/pulls/{pr['number']}/"
                    f"reviews/{review_id}/dismissals"
                )
                payload = {"message": action.value or "Review dismissed"}
                self.client.put(path, payload=payload)
        elif action.type == ActionType.rerun_checks and action.metadata:
            check_run_url = action.metadata.get("url")
            if check_run_url:
                self.client.post(check_run_url, payload=None)
        # Extend with other action types as needed.


__all__ = ["GitHubClient", "ActionExecutor"]
