"""GitHub REST API client."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


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


__all__ = ["GitHubClient"]
