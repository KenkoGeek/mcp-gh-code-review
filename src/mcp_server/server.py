"""Minimal MCP server - GraphQL threads + REST replies."""

from __future__ import annotations

import os
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from .actions import GitHubClient
from .bot_detector import is_bot
from .graphql_client import GitHubGraphQLClient
from .jsonrpc import JSONRPCServer
from .schemas import SubmitPendingReviewRequest, schema_for


@dataclass(slots=True)
class MCPServer:
    """MCP server with 4 tools: review_pr, reply, get_threads, submit_review."""
    
    token: str
    client: GitHubClient
    graphql: GitHubGraphQLClient
    
    @classmethod
    def create(cls, token: str) -> MCPServer:
        client = GitHubClient(token=token)
        graphql = GitHubGraphQLClient(token=token)
        return cls(token=token, client=client, graphql=graphql)
    
    def _get_repo(self) -> tuple[str, str]:
        """Get owner/repo from git remote."""
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            raise ValueError("Not in a git repository")
        
        url = result.stdout.strip()
        if "github.com" not in url:
            raise ValueError("Not a GitHub repository")
        
        if url.startswith("git@"):
            parts = url.split(":")[1].replace(".git", "").split("/")
        else:
            parts = url.split("/")[-2:]
            parts[1] = parts[1].replace(".git", "")
        
        return parts[0], parts[1]
    
    async def review_pr(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get PR with threads (GraphQL) + reviews (REST)."""
        pr_number = params["pr_number"]
        owner, repo = self._get_repo()
        
        # GraphQL: threads with isResolved
        threads_data = await self.graphql.get_review_threads(owner, repo, pr_number)
        
        # REST: PR info + reviews
        pr_response = self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        reviews_response = self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
        
        # Annotate threads with bot detection
        threads = threads_data.get("threads", [])
        for thread in threads:
            for comment in thread.get("comments", {}).get("nodes", []):
                author = comment.get("author", {})
                if author:
                    author["is_bot"] = is_bot(author.get("login", ""))
        
        return {
            "pr_info": pr_response.json(),
            "reviews": reviews_response.json(),
            "threads": threads,
            "threads_count": threads_data.get("count", 0)
        }
    
    async def reply_to_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reply to inline comment using databaseId."""
        pr_number = params["pr_number"]
        database_id = int(params["comment_id"])  # Must be integer
        reply_text = params["reply_text"]
        owner, repo = self._get_repo()
        
        path = f"/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        payload = {"body": reply_text, "in_reply_to": database_id}
        
        self.client.post(path, payload=payload)
        return {"success": True}
    
    async def get_review_threads(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get review threads with isResolved status."""
        pr_number = params["pr_number"]
        owner, repo = self._get_repo()
        return await self.graphql.get_review_threads(owner, repo, pr_number)
    
    async def submit_pending_review(self, params: dict[str, Any]) -> dict[str, Any]:
        """Submit pending review via GraphQL."""
        request = SubmitPendingReviewRequest.model_validate(params)
        owner, repo = self._get_repo()
        return await self.graphql.submit_pending_review(
            owner, repo, request.pr_number, request.review_id, request.event, request.body
        )
    
    async def health(self, params: dict[str, Any]) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "ok",
            "rate_limit": {
                "remaining": self.client.rate_limit_remaining,
                "reset": self.client.rate_limit_reset
            }
        }
    
    def handlers(self) -> dict:
        """JSON-RPC handlers."""
        return {
            "review_pr": self._wrap(self.review_pr),
            "reply_to_comment": self._wrap(self.reply_to_comment),
            "get_review_threads": self._wrap(self.get_review_threads),
            "submit_pending_review": self._wrap(self.submit_pending_review),
            "health": self._wrap(self.health),
        }
    
    def _wrap(
        self, func: Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]
    ) -> Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]:
        async def wrapper(params: dict[str, Any]) -> dict[str, Any]:
            return await func(params)
        return wrapper
    
    def schemas(self) -> dict:
        """Tool schemas."""
        return {
            "review_pr": {
                "type": "object",
                "properties": {"pr_number": {"type": "integer"}},
                "required": ["pr_number"]
            },
            "reply_to_comment": {
                "type": "object",
                "properties": {
                    "pr_number": {"type": "integer"},
                    "comment_id": {"type": "string"},
                    "reply_text": {"type": "string"}
                },
                "required": ["pr_number", "comment_id", "reply_text"]
            },
            "get_review_threads": {
                "type": "object",
                "properties": {"pr_number": {"type": "integer"}},
                "required": ["pr_number"]
            },
            "submit_pending_review": schema_for(SubmitPendingReviewRequest),
            "health": {"type": "object", "properties": {}}
        }
    
    async def serve_stdio(self) -> None:
        """Serve via stdio."""
        server = JSONRPCServer(self.handlers(), schemas=self.schemas())
        await server.serve_stdio()


async def run_stdio() -> None:
    """Entry point."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable required")
    
    server = MCPServer.create(token)
    await server.serve_stdio()


__all__ = ["MCPServer", "run_stdio"]
