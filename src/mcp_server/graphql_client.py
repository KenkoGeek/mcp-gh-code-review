"""GraphQL client for GitHub API - focused on pending reviews."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class GitHubGraphQLClient:
    """GitHub GraphQL API client for pending reviews and review threads."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=30.0)
        self.rate_limit_remaining: int | None = None
        self.rate_limit_reset: int | None = None
        self.rate_limit_cost: int | None = None
        self.rate_limit_used: int | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubGraphQLClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def _update_rate_limits(self, response: httpx.Response) -> None:
        headers = response.headers
        if "X-RateLimit-Remaining" in headers:
            self.rate_limit_remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            self.rate_limit_reset = int(headers["X-RateLimit-Reset"])
        if "X-RateLimit-Cost" in headers:
            self.rate_limit_cost = int(headers["X-RateLimit-Cost"])
        if "X-RateLimit-Used" in headers:
            self.rate_limit_used = int(headers["X-RateLimit-Used"])

    async def query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute GraphQL query."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        operation = operation_name or "anonymous"

        try:
            logger.info("github_graphql_request", operation=operation)
            response = await self._client.post(
                self.base_url,
                headers=self.headers,
                json=payload,
            )
            self._update_rate_limits(response)
            response.raise_for_status()
            result: dict[str, Any] = response.json()

            if "errors" in result:
                logger.error(
                    "github_graphql_error",
                    operation=operation,
                    errors=result["errors"],
                    rate_limit_remaining=self.rate_limit_remaining,
                )
                error_msg = result["errors"][0].get("message", "Unknown GraphQL error")
                raise ValueError(f"GraphQL error: {error_msg}")

            logger.info(
                "github_graphql_success",
                operation=operation,
                rate_limit_remaining=self.rate_limit_remaining,
                rate_limit_used=self.rate_limit_used,
                rate_limit_cost=self.rate_limit_cost,
            )
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                "github_graphql_http_error",
                operation=operation,
                status=e.response.status_code,
            )
            if e.response.status_code == 401:
                raise ValueError("Invalid GitHub token") from e
            if e.response.status_code == 404:
                raise ValueError("Resource not found") from e
            if e.response.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded or forbidden") from e
            raise ValueError(f"GitHub API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("github_graphql_connection_failed", operation=operation, error=str(e))
            raise ValueError(f"GitHub API connection failed: {e}") from e

    async def get_pending_reviews(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Get pending reviews with inline comments."""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $number) {
              reviews(first: 10, states: [PENDING]) {
                nodes {
                  id
                  databaseId
                  state
                  body
                  author {
                    login
                  }
                  comments(first: 10) {
                    nodes {
                      id
                      databaseId
                      body
                      path
                      line
                      originalLine
                      diffHunk
                      createdAt
                      author {
                        login
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "owner": owner,
            "repo": repo,
            "number": pr_number
        }

        result = await self.query(query, variables, operation_name="get_pending_reviews")

        if "errors" in result:
            logger.error("graphql_error", errors=result["errors"])
            return {"error": result["errors"]}

        reviews = result["data"]["repository"]["pullRequest"]["reviews"]["nodes"]

        return {
            "pending_reviews": reviews,
            "count": len(reviews),
            "has_comments": any(len(r["comments"]["nodes"]) > 0 for r in reviews)
        }

    async def submit_pending_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_id: str,
        event: str,
        body: str = "",
    ) -> dict[str, Any]:
        """Submit pending review via GraphQL mutation."""
        mutation = """
        mutation($input: SubmitPullRequestReviewInput!) {
          submitPullRequestReview(input: $input) {
            pullRequestReview {
              id
              databaseId
              state
            }
          }
        }
        """

        variables = {
            "input": {
                "pullRequestReviewId": review_id,
                "event": event.upper(),
                "body": body
            }
        }

        result = await self.query(mutation, variables, operation_name="submit_pending_review")

        if "errors" in result:
            return {"error": result["errors"]}

        return {
            "success": True,
            "review": result["data"]["submitPullRequestReview"]["pullRequestReview"]
        }

    async def get_review_threads(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Get review threads with isResolved status."""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $number) {
              reviewThreads(first: 100) {
                nodes {
                  id
                  isResolved
                  comments(first: 20) {
                    nodes {
                      id
                      databaseId
                      body
                      path
                      line
                      author {
                        login
                      }
                      createdAt
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"owner": owner, "repo": repo, "number": pr_number}
        result = await self.query(query, variables, operation_name="get_review_threads")

        if "errors" in result:
            logger.error("graphql_error", errors=result["errors"])
            return {"error": result["errors"]}

        threads = result["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
        return {"threads": threads, "count": len(threads)}


__all__ = ["GitHubGraphQLClient"]
