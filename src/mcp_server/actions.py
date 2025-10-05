"""GitHub REST API client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def _handle_http_error(e: httpx.HTTPStatusError) -> NoReturn:
    """Extract GitHub error message and raise appropriate ValueError."""
    try:
        error_data = e.response.json()
        gh_message = error_data.get("message", "Unknown error")
    except Exception:
        gh_message = e.response.text or "Unknown error"
    
    if e.response.status_code == 401:
        raise ValueError(f"Invalid GitHub token: {gh_message}") from e
    if e.response.status_code == 404:
        raise ValueError(f"Resource not found: {gh_message}") from e
    if e.response.status_code in (403, 429):
        raise ValueError(f"GitHub API rate limit exceeded: {gh_message}") from e
    raise ValueError(f"GitHub API error ({e.response.status_code}): {gh_message}") from e


@dataclass(slots=True)
class GitHubClient:
    token: str
    base_url: str = "https://api.github.com"
    _client: httpx.Client = field(init=False, repr=False)
    rate_limit_remaining: int = field(default=5000, init=False)
    rate_limit_reset: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._client = httpx.Client(timeout=10.0, headers=self._headers())

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}"
        }

    def _update_rate_limits(self, response: httpx.Response) -> None:
        if "X-RateLimit-Remaining" in response.headers:
            self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in response.headers:
            self.rate_limit_reset = int(response.headers["X-RateLimit-Reset"])

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    def post(self, path: str, payload: dict | None = None) -> httpx.Response:
        try:
            response = self._client.post(f"{self.base_url}{path}", json=payload)
            self._update_rate_limits(response)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            _handle_http_error(e)
        except httpx.RequestError as e:
            raise ValueError(f"GitHub API connection failed: {e}") from e

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    def patch(self, path: str, payload: dict | None = None) -> httpx.Response:
        try:
            response = self._client.patch(f"{self.base_url}{path}", json=payload)
            self._update_rate_limits(response)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            _handle_http_error(e)
        except httpx.RequestError as e:
            raise ValueError(f"GitHub API connection failed: {e}") from e

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    def get(self, path: str) -> httpx.Response:
        try:
            response = self._client.get(f"{self.base_url}{path}")
            self._update_rate_limits(response)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            _handle_http_error(e)
        except httpx.RequestError as e:
            raise ValueError(f"GitHub API connection failed: {e}") from e

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    def put(self, path: str, payload: dict | None = None) -> httpx.Response:
        try:
            response = self._client.put(f"{self.base_url}{path}", json=payload)
            self._update_rate_limits(response)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            _handle_http_error(e)
        except httpx.RequestError as e:
            raise ValueError(f"GitHub API connection failed: {e}") from e

    def close(self) -> None:
        self._client.close()


__all__ = ["GitHubClient"]
