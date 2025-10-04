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
        logger.debug("rate_limit_updated", remaining=self.rate_limit_remaining, reset=self.rate_limit_reset)

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

    def close(self) -> None:
        self._client.close()


@dataclass(slots=True)
class ActionExecutor:
    client: GitHubClient

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
            if pr:
                path = f"/repos/{pr['owner']}/{pr['repo']}/issues/{pr['number']}/labels"
                self.client.post(path, payload={"labels": [action.value]})
        elif action.type == ActionType.comment and action.metadata:
            pr = action.metadata.get("pr")
            if pr:
                path = f"/repos/{pr['owner']}/{pr['repo']}/issues/{pr['number']}/comments"
                self.client.post(path, payload={"body": action.value})
        elif action.type == ActionType.rerun_checks and action.metadata:
            check_run_url = action.metadata.get("url")
            if check_run_url:
                self.client.post(check_run_url, payload=None)
        # Extend with other action types as needed.


__all__ = ["GitHubClient", "ActionExecutor"]
