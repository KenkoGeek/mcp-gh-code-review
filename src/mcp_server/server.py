"""Minimal MCP server - GraphQL threads + REST replies."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog

from .actions import GitHubClient
from .bot_detector import is_bot
from .graphql_client import GitHubGraphQLClient
from .jsonrpc import JSONRPCServer
from .schemas import SubmitPendingReviewRequest, schema_for

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MCPServer:
    """MCP server with 8 tools: 5 PR + 3 issues + health."""
    
    token: str
    client: GitHubClient
    graphql: GitHubGraphQLClient
    
    @classmethod
    def create(cls, token: str) -> MCPServer:
        client = GitHubClient(token=token)
        graphql = GitHubGraphQLClient(token=token)
        return cls(token=token, client=client, graphql=graphql)
    
    def _get_repo(self) -> tuple[str, str]:
        """Get owner/repo from git remote or env var."""
        # Try env var first (GITHUB_REPOSITORY=owner/repo)
        env_repo = os.environ.get("GITHUB_REPOSITORY")
        if env_repo and "/" in env_repo:
            parts = env_repo.split("/", 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                return parts[0].strip(), parts[1].strip()
            raise ValueError(
                f"Invalid GITHUB_REPOSITORY format: '{env_repo}'. "
                "Expected format: 'owner/repo'"
            )
        
        # Find .git directory by walking up from cwd
        current = Path.cwd()
        for parent in [current, *current.parents]:
            if (parent / ".git").exists():
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=parent, capture_output=True, text=True, timeout=5
                    )
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                    continue
                
                if result.returncode == 0:
                    url = result.stdout.strip()
                    if url.startswith("git@github.com:"):
                        # SSH format: git@github.com:owner/repo.git
                        parts = url.split(":")[1].replace(".git", "").split("/")
                        if len(parts) >= 2 and parts[0] and parts[1]:
                            return parts[0], parts[1]
                    else:
                        # HTTPS format
                        parsed = urlparse(url)
                        if parsed.netloc == "github.com":
                            path_parts = parsed.path.strip("/").replace(".git", "").split("/")
                            if len(path_parts) >= 2 and path_parts[0] and path_parts[1]:
                                return path_parts[0], path_parts[1]
        
        raise ValueError(
            "Could not detect GitHub repository. "
            "Set GITHUB_REPOSITORY=owner/repo environment variable or run from a git repository " \
            "with GitHub remote."
        )
    
    async def review_pr(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get PR with threads (GraphQL) + reviews (REST)."""
        pr_number = params["pr_number"]
        owner, repo = self._get_repo()
        logger.info("review_pr_start", pr_number=pr_number, owner=owner, repo=repo)
        
        # Get authenticated user
        user_response = self.client.get("/user")
        authenticated_user = user_response.json()["login"]
        
        # GraphQL: threads with isResolved
        threads_data = await self.graphql.get_review_threads(owner, repo, pr_number)
        
        # REST: PR info + reviews
        pr_response = self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        reviews_response = self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
        
        # Annotate threads with bot detection and own comment detection
        threads = threads_data.get("threads", [])
        for thread in threads:
            for comment in thread.get("comments", {}).get("nodes", []):
                author = comment.get("author", {})
                if author:
                    login = author.get("login", "")
                    author["is_bot"] = is_bot(login)
                    author["is_me"] = login == authenticated_user
        
        logger.info(
            "review_pr_complete",
            pr_number=pr_number,
            threads_count=threads_data.get("count", 0),
            authenticated_user=authenticated_user,
        )
        return {
            "pr_info": pr_response.json(),
            "reviews": reviews_response.json(),
            "threads": threads,
            "threads_count": threads_data.get("count", 0),
            "authenticated_user": authenticated_user,
            "_guidance": (
                "When replying: "
                "is_bot=true → short replies (1-2 lines, e.g. '✅ LGTM'), "
                "is_bot=false → detailed replies, "
                "is_me=true → skip (your own comments)"
            )
        }
    
    async def reply_to_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reply to inline comment using databaseId."""
        pr_number = params["pr_number"]
        database_id = int(params["comment_id"])  # Must be integer
        reply_text = params["reply_text"]
        owner, repo = self._get_repo()
        
        logger.info("reply_to_comment", pr_number=pr_number, comment_id=database_id, owner=owner, repo=repo)
        
        path = f"/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        payload = {"body": reply_text, "in_reply_to": database_id}
        
        self.client.post(path, payload=payload)
        logger.info("reply_to_comment_success", pr_number=pr_number, comment_id=database_id)
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
    
    async def list_issues(self, params: dict[str, Any]) -> dict[str, Any]:
        """List all issues (excluding PRs)."""
        owner, repo = self._get_repo()
        state = params.get("state", "open")  # open, closed, all
        
        logger.info("list_issues_start", owner=owner, repo=repo, state=state)
        
        try:
            # Get all issues (includes PRs)
            response = self.client.get(f"/repos/{owner}/{repo}/issues?state={state}&per_page=100")
            all_items = response.json()
            
            # Filter out PRs - only keep real issues
            issues = [
                item for item in all_items 
                if "pull_request" not in item or item["pull_request"] is None
            ]
            
            logger.info("list_issues_complete", count=len(issues), state=state)
            return {"issues": issues, "count": len(issues)}
        except Exception as e:
            logger.error("list_issues_failed", error=str(e))
            raise
    
    async def review_issue(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get issue with comments."""
        issue_number = params["issue_number"]
        if issue_number <= 0:
            raise ValueError("issue_number must be a positive integer")
        
        owner, repo = self._get_repo()
        logger.info("review_issue_start", issue_number=issue_number, owner=owner, repo=repo)
        
        try:
            # Get authenticated user
            user_response = self.client.get("/user")
            authenticated_user = user_response.json()["login"]
            
            # Get issue + comments
            issue_response = self.client.get(f"/repos/{owner}/{repo}/issues/{issue_number}")
            comments_response = self.client.get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")
        except Exception as e:
            logger.error("review_issue_failed", issue_number=issue_number, error=str(e))
            raise
        
        issue_data = issue_response.json()
        
        # GitHub /issues endpoint returns both issues and PRs
        # Reject PRs - only accept real issues
        if "pull_request" in issue_data and issue_data["pull_request"] is not None:
            raise ValueError(f"#{issue_number} is a pull request, not an issue. Use review_pr instead.")
        
        comments = comments_response.json()
        
        # Annotate comments with bot detection and own comment detection
        for comment in comments:
            user = comment.get("user", {})
            if user:
                login = user.get("login", "")
                user["is_bot"] = is_bot(login)
                user["is_me"] = login == authenticated_user
        
        logger.info(
            "review_issue_complete",
            issue_number=issue_number,
            comments_count=len(comments),
            authenticated_user=authenticated_user,
        )
        return {
            "issue": issue_data,
            "comments": comments,
            "authenticated_user": authenticated_user,
            "_guidance": (
                "When replying: "
                "is_bot=true → short replies (1-2 lines, e.g. \"Thanks for the update\"), "
                "is_bot=false → detailed replies, "
                "is_me=true → skip (your own comments)"
            )
        }
    
    async def reply_to_issue_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reply to issue comment."""
        issue_number = params["issue_number"]
        reply_text = params["reply_text"]
        
        if not reply_text or not reply_text.strip():
            raise ValueError("reply_text cannot be empty or whitespace")
        
        owner, repo = self._get_repo()
        logger.info("reply_to_issue_comment", issue_number=issue_number, owner=owner, repo=repo)
        
        try:
            path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
            payload = {"body": reply_text}
            
            response = self.client.post(path, payload=payload)
            response.raise_for_status()
            logger.info("reply_to_issue_comment_success", issue_number=issue_number)
            return {"success": True}
        except Exception as e:
            logger.error("reply_to_issue_comment_failed", issue_number=issue_number, error=str(e))
            raise
    
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
            "list_issues": self._wrap(self.list_issues),
            "review_issue": self._wrap(self.review_issue),
            "reply_to_issue_comment": self._wrap(self.reply_to_issue_comment),
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
            "list_issues": {
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["open", "closed", "all"]}
                }
            },
            "review_issue": {
                "type": "object",
                "properties": {"issue_number": {"type": "integer"}},
                "required": ["issue_number"]
            },
            "reply_to_issue_comment": {
                "type": "object",
                "properties": {
                    "issue_number": {"type": "integer"},
                    "reply_text": {"type": "string"}
                },
                "required": ["issue_number", "reply_text"]
            },
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
