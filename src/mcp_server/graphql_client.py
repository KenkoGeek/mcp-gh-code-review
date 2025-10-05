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
    
    async def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute GraphQL query."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
    
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
        
        result = await self.query(query, variables)
        
        if "errors" in result:
            logger.error("graphql_error", errors=result["errors"])
            return {"error": result["errors"]}
        
        reviews = result["data"]["repository"]["pullRequest"]["reviews"]["nodes"]
        
        return {
            "pending_reviews": reviews,
            "count": len(reviews),
            "has_comments": any(len(r["comments"]["nodes"]) > 0 for r in reviews)
        }
    
    async def submit_pending_review(self, owner: str, repo: str, pr_number: int, 
                                  review_id: str, event: str, body: str = "") -> dict[str, Any]:
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
        
        result = await self.query(mutation, variables)
        
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
        result = await self.query(query, variables)
        
        if "errors" in result:
            logger.error("graphql_error", errors=result["errors"])
            return {"error": result["errors"]}
        
        threads = result["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
        return {"threads": threads, "count": len(threads)}


__all__ = ["GitHubGraphQLClient"]