"""Apply actions to GitHub."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import GitHubConfig
from .schemas import Action, ActionResult, ActionType


@dataclass(slots=True)
class GitHubClient:
    config: GitHubConfig
    base_url: str = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        return headers

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def post(self, path: str, payload: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{self.base_url}{path}", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def patch(self, path: str, payload: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=10.0) as client:
            response = client.patch(f"{self.base_url}{path}", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response


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
