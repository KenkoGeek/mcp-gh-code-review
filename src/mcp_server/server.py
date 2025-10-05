"""MCP server entry point binding all tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any

import structlog

from .actions import ActionExecutor, GitHubClient
from .classifier import ActorClassifier
from .config import PolicyConfig, ServerConfig, load_policy
from .graphql_client import GitHubGraphQLClient
from .jsonrpc import JSONRPCServer
from .orchestrator import PROrchestrator
from .responder import Responder
from .schemas import (
    ActionType,
    ApplyActionsRequest,
    ApplyActionsResponse,
    ClassificationResult,
    ClassifyActorRequest,
    GenerateReplyRequest,
    HealthResponse,
    ManagePendingReviewRequest,
    ManagePendingReviewResponse,
    MapInlineThreadRequest,
    SetPolicyRequest,
    TriageEventRequest,
    schema_for,
)

# Context schemas imported dynamically to avoid circular imports
from .storage import Storage
from .thread_manager import ThreadManager
from .triage import TriageEngine

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MCPServer:
    """Register MCP tools and expose JSON-RPC handler."""

    config: ServerConfig
    policy: PolicyConfig
    classifier: ActorClassifier
    responder: Responder
    triage_engine: TriageEngine
    action_executor: ActionExecutor
    thread_manager: ThreadManager
    orchestrator: PROrchestrator
    graphql_client: GitHubGraphQLClient

    @classmethod
    def create(cls, config: ServerConfig) -> MCPServer:
        policy = load_policy(config.policy_path) if config.policy_path else PolicyConfig()
        classifier = ActorClassifier(config.bot_actors)
        responder = Responder()
        triage_engine = TriageEngine(classifier=classifier, policy=policy)
        action_executor = ActionExecutor(client=GitHubClient(config=config.github))
        storage = Storage(config.db_path)
        thread_manager = ThreadManager(storage=storage)
        graphql_client = GitHubGraphQLClient(config.github.token)
        server = cls(
            config=config,
            policy=policy,
            classifier=classifier,
            responder=responder,
            triage_engine=triage_engine,
            action_executor=action_executor,
            thread_manager=thread_manager,
            orchestrator=None,  # Will be set after creation
            graphql_client=graphql_client,
        )
        server.orchestrator = PROrchestrator(server)
        return server

    def jsonrpc_handlers(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Return JSON-RPC method handlers."""
        return {
            # Core workflow - single entry point
            "review_pr": self._wrap(self.review_pr),
            
            # Essential actions
            "apply_actions": self._wrap(self.apply_actions),
            "generate_reply": self._wrap(self.generate_reply),
            
            # Pending reviews (GraphQL)
            "get_pending_reviews": self._wrap(self.get_pending_reviews),
            "submit_pending_review": self._wrap(self.submit_pending_review),
            
            # System management
            "health": self._wrap(self.health),
            "set_policy": self._wrap(self.set_policy),
        }

    def _wrap(
        self, func: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    ) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
        async def wrapper(params: dict[str, Any]) -> dict[str, Any]:
            return await func(params)

        return wrapper

    async def classify_actor(self, params: dict[str, Any]) -> dict[str, Any]:
        request = ClassifyActorRequest.model_validate(params)
        result = self.classifier.classify(request.login, request.name)
        return ClassificationResult(**asdict(result)).model_dump()

    async def triage_event(self, params: dict[str, Any]) -> dict[str, Any]:
        request = TriageEventRequest.model_validate(params)
        triaged = self.triage_engine.triage(request.event)
        return triaged.model_dump()

    async def generate_reply(self, params: dict[str, Any]) -> dict[str, Any]:
        request = GenerateReplyRequest.model_validate(params)
        response = self.responder.generate(request)
        return response.model_dump()

    async def apply_actions(self, params: dict[str, Any]) -> dict[str, Any]:
        request = ApplyActionsRequest.model_validate(params)
        
        # Auto-detect PR context and add to actions that need it
        context = self._auto_detect_context()
        if "error" not in context:
            # Get PR number from first action or default to 1
            pr_number = next(
                (action.metadata.get("pr_number") for action in request.actions 
                 if "pr_number" in action.metadata), 1
            )
            
            # Check for pending reviews and optimize action types
            try:
                pr_data = await self.get_pr_data({
                    "pr_number": pr_number, 
                    "include": ["pending_reviews"]
                })
                has_pending_review = (
                    "pending_reviews" in pr_data and 
                    pr_data["pending_reviews"]["count"] > 0
                )
            except Exception as e:
                logger.warning("failed_to_check_pending_reviews", error=str(e))
                has_pending_review = False
            
            # Add PR context and optimize action types
            for action in request.actions:
                if (action.type in [ActionType.comment, ActionType.apply_label, 
                                   ActionType.add_review_comment] and 
                    "pr" not in action.metadata):
                    action.metadata["pr"] = {
                        "owner": context["owner"],
                        "repo": context["repo"],
                        "number": pr_number
                    }
                
                # Optimize comment actions based on pending review status
                if action.type == ActionType.comment and has_pending_review:
                    # If there's a pending review, use the special handler
                    action.type = ActionType.reply_to_pending_review
        
        # Log action optimization for debugging
        logger.info("optimized_actions", 
                   action_types=[action.type.value for action in request.actions],
                   has_pending_review=has_pending_review)
        
        results = self.action_executor.apply(
            request.actions, dry_run=request.dry_run or self.config.dry_run
        )
        return ApplyActionsResponse(results=results).model_dump()

    async def map_inline_thread(self, params: dict[str, Any]) -> dict[str, Any]:
        request = MapInlineThreadRequest.model_validate(params)
        response = await self.thread_manager.map_thread(request)
        return response.model_dump()

    async def set_policy(self, params: dict[str, Any]) -> dict[str, Any]:
        request = SetPolicyRequest.model_validate(params)
        self.policy = PolicyConfig(**request.policy)
        self.triage_engine.policy = self.policy
        return {"ok": True}

    async def health(self, params: dict[str, Any]) -> dict[str, Any]:
        db_healthy = self.thread_manager.storage.health_check()
        rate_limit = {
            "remaining": self.action_executor.client.rate_limit_remaining,
            "reset": self.action_executor.client.rate_limit_reset,
        }
        return HealthResponse(
            version="0.1.0",
            database_healthy=db_healthy,
            rate_limit=rate_limit,
        ).model_dump()

    def _auto_detect_context(self) -> dict[str, Any]:
        """Auto-detect repo context from .git directory."""
        import subprocess
        from pathlib import Path
        
        # Check if we're in a git repository
        if not Path(".git").exists():
            return {"error": "Not in a git repository root. Please run from project root directory."}
        
        try:
            import shutil
            git_path = shutil.which("git")
            if not git_path:
                return {"error": "Git command not found in PATH"}
            
            result = subprocess.run(
                [git_path, "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                if url.startswith("https://github.com/") or url.startswith("git@github.com:"):
                    if url.startswith("git@"):
                        parts = url.split(":")[1].replace(".git", "").split("/")
                    else:
                        parts = url.split("/")[-2:]
                        parts[1] = parts[1].replace(".git", "")
                    return {"owner": parts[0], "repo": parts[1]}
            return {"error": "Could not detect GitHub repo from git remote"}
        except Exception as e:
            return {"error": f"Git command failed: {e}"}

    async def fetch_pr_info(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch PR details from GitHub API."""
        # Auto-detect context if not provided
        if not params.get("owner") or not params.get("repo"):
            context = self._auto_detect_context()
            if "error" in context:
                return context
            owner, repo = context["owner"], context["repo"]
        else:
            owner, repo = params["owner"], params["repo"]
        
        pr_number = params.get("pr_number")
        
        if not all([owner, repo, pr_number]):
            return {"error": "Missing owner, repo, or pr_number. Set context first."}
        
        if self.config.dry_run:
            return {
                "pr_info": {
                    "number": pr_number,
                    "title": "[DRY RUN] Sample PR Title",
                    "state": "open",
                    "user": {"login": "sample-user"},
                    "head": {"ref": "feature-branch"},
                    "base": {"ref": "main"}
                },
                "dry_run": True
            }
        
        try:
            path = f"/repos/{owner}/{repo}/pulls/{pr_number}"
            response = self.action_executor.client.get(path)
            return {"pr_info": response.json(), "path": path}
        except Exception as e:
            return {"error": str(e)}

    async def get_pr_data(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive PR data: info, reviews, comments, inline comments, and pending reviews."""
        # Auto-detect context if not provided
        if not params.get("owner") or not params.get("repo"):
            context = self._auto_detect_context()
            if "error" in context:
                return context
            owner, repo = context["owner"], context["repo"]
        else:
            owner, repo = params["owner"], params["repo"]
        
        pr_number = params.get("pr_number")
        include_types = params.get("include", ["info", "reviews", "comments", "inline_comments", "pending_reviews"])
        
        if not all([owner, repo, pr_number]):
            return {"error": "Missing pr_number parameter"}
        
        if self.config.dry_run:
            return {
                "pr_info": {
                    "number": pr_number,
                    "title": "[DRY RUN] Sample PR Title",
                    "state": "open",
                    "user": {"login": "sample-user"}
                } if "info" in include_types else None,
                "reviews": [
                    {
                        "id": 1,
                        "user": {"login": "reviewer1"},
                        "state": "CHANGES_REQUESTED",
                        "body": "[DRY RUN] Please fix error handling"
                    }
                ] if "reviews" in include_types else None,
                "comments": [
                    {
                        "id": 1,
                        "user": {"login": "reviewer1"},
                        "body": "[DRY RUN] Great work!"
                    }
                ] if "comments" in include_types else None,
                "inline_comments": [
                    {
                        "id": 123,
                        "user": {"login": "reviewer1"},
                        "body": "[DRY RUN] Optimize this function",
                        "path": "src/server.py",
                        "line": 42
                    }
                ] if "inline_comments" in include_types else None,
                "dry_run": True
            }
        
        result = {}
        
        try:
            # PR Info
            if "info" in include_types:
                response = self.action_executor.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
                result["pr_info"] = response.json()
            
            # Reviews
            if "reviews" in include_types:
                response = self.action_executor.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
                result["reviews"] = response.json()
            
            # General comments
            if "comments" in include_types:
                response = self.action_executor.client.get(f"/repos/{owner}/{repo}/issues/{pr_number}/comments")
                result["comments"] = response.json()
            
            # Inline comments
            if "inline_comments" in include_types:
                response = self.action_executor.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}/comments")
                result["inline_comments"] = response.json()
            
            # Pending reviews analysis
            if "pending_reviews" in include_types and "reviews" in result:
                pending_reviews = [r for r in result["reviews"] if r.get("state") == "PENDING"]
                result["pending_reviews"] = {
                    "count": len(pending_reviews),
                    "reviews": pending_reviews,
                    "can_add_comments": len(pending_reviews) > 0,
                    "needs_submission": len(pending_reviews) > 0
                }
            
            # Add comprehensive analysis
            if "reviews" in result and "inline_comments" in result:
                # Map inline comments to their review threads
                inline_by_thread = {}
                for comment in result["inline_comments"]:
                    thread_key = f"{comment.get('path', 'unknown')}:{comment.get('line', 0)}"
                    if thread_key not in inline_by_thread:
                        inline_by_thread[thread_key] = []
                    inline_by_thread[thread_key].append(comment)
                
                result["analysis"] = {
                    "total_reviews": len(result["reviews"]),
                    "pending_count": len([r for r in result["reviews"] if r.get("state") == "PENDING"]),
                    "changes_requested_count": len([r for r in result["reviews"] if r.get("state") == "CHANGES_REQUESTED"]),
                    "approved_count": len([r for r in result["reviews"] if r.get("state") == "APPROVED"]),
                    "inline_threads": inline_by_thread,
                    "unanswered_comments": [
                        c for c in result["inline_comments"] 
                        if not any(ic.get("in_reply_to_id") == c["id"] for ic in result["inline_comments"])
                    ]
                }
            
            return result
        except Exception as e:
            return {"error": str(e)}

    async def analyze_pr_reviews(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze PR reviews and categorize by criticality and type."""
        # Get all PR data first
        pr_data = await self.get_pr_data({"pr_number": params.get("pr_number")})
        if "error" in pr_data:
            return pr_data
        
        # Analyze reviews
        reviews = pr_data.get("reviews", [])
        inline_comments = pr_data.get("inline_comments", [])
        
        # Analyze conversation threads
        from .thread_analyzer import ThreadAnalyzer
        authenticated_user = await self._get_authenticated_user()
        analyzer = ThreadAnalyzer(self.config.bot_actors, authenticated_user)
        threads = analyzer.analyze_threads(inline_comments)
        priority_threads = analyzer.get_priority_threads(threads)
        
        analysis = {
            "summary": {
                "total_reviews": len(reviews),
                "changes_requested": len([r for r in reviews if r.get("state") == "CHANGES_REQUESTED"]),
                "approved": len([r for r in reviews if r.get("state") == "APPROVED"]),
                "total_inline_comments": len(inline_comments),
                "conversation_threads": len(threads),
                "threads_needing_response": len(priority_threads)
            },
            "critical_reviews": [],
            "blocking_reviews": [],
            "suggestions": [],
            "conversation_threads": [
                {
                    "thread_id": t.thread_id,
                    "path": t.path,
                    "line": t.line,
                    "participants": [p.login for p in t.participants],
                    "needs_response": t.needs_response,
                    "last_external_comment_id": t.last_external_comment_id,
                    "priority": "high" if t.needs_response else "low"
                } for t in threads
            ],
            "priority_responses": [
                {
                    "comment_id": t.last_external_comment_id,
                    "path": t.path,
                    "line": t.line,
                    "participants": [p.login for p in t.participants if not p.is_bot]
                } for t in priority_threads if t.last_external_comment_id
            ],
            "inline_threads": {}
        }
        
        # Categorize reviews by criticality
        for review in reviews:
            if review.get("state") == "CHANGES_REQUESTED":
                # Classify actor
                classification = self.classifier.classify(review["user"]["login"])
                
                review_item = {
                    "review_id": review["id"],
                    "author": review["user"]["login"],
                    "actor_type": classification.actor_type.value,
                    "body": review.get("body", ""),
                    "submitted_at": review.get("submitted_at")
                }
                
                # Determine criticality based on keywords
                body_lower = review.get("body", "").lower()
                if any(word in body_lower for word in ["security", "critical", "urgent", "breaking"]):
                    analysis["critical_reviews"].append(review_item)
                else:
                    analysis["blocking_reviews"].append(review_item)
            
            elif review.get("state") == "COMMENTED":
                analysis["suggestions"].append({
                    "review_id": review["id"],
                    "author": review["user"]["login"],
                    "body": review.get("body", "")
                })
        
        # Group inline comments by file/line
        for comment in inline_comments:
            file_line = f"{comment.get('path', 'unknown')}:{comment.get('line', 0)}"
            if file_line not in analysis["inline_threads"]:
                analysis["inline_threads"][file_line] = []
            
            analysis["inline_threads"][file_line].append({
                "comment_id": comment["id"],
                "author": comment["user"]["login"],
                "body": comment["body"],
                "created_at": comment.get("created_at")
            })
        
        return analysis
    
    async def _get_authenticated_user(self) -> str:
        """Get the authenticated user from GitHub API."""
        try:
            response = self.action_executor.client.get("/user")
            user_data = response.json()
            return user_data.get("login", "unknown")
        except Exception:
            return "unknown"

    async def manage_pending_review(self, params: dict[str, Any]) -> dict[str, Any]:
        """Manage pending reviews: submit, dismiss, or add comments."""
        request = ManagePendingReviewRequest.model_validate(params)
        
        # Auto-detect context
        context = self._auto_detect_context()
        if "error" in context:
            return context
        
        owner, repo = context["owner"], context["repo"]
        pr_number = request.pr_number
        
        if self.config.dry_run:
            return ManagePendingReviewResponse(
                success=True,
                review_id=12345,
                message=f"[DRY RUN] Would {request.action} pending review for PR {pr_number}"
            ).model_dump()
        
        try:
            if request.action == "submit":
                # Submit pending review
                path = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
                payload = {
                    "event": request.event,
                    "body": request.body or ""
                }
                if request.comments:
                    payload["comments"] = request.comments
                
                response = self.action_executor.client.post(path, payload=payload)
                result = response.json()
                
                return ManagePendingReviewResponse(
                    success=True,
                    review_id=result.get("id"),
                    message=f"Review submitted with event: {request.event}"
                ).model_dump()
            
            elif request.action == "dismiss":
                # First get pending reviews to find the one to dismiss
                reviews_path = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
                reviews_response = self.action_executor.client.get(reviews_path)
                reviews = reviews_response.json()
                
                pending_review = next((r for r in reviews if r["state"] == "PENDING"), None)
                if not pending_review:
                    return ManagePendingReviewResponse(
                        success=False,
                        message="No pending review found to dismiss"
                    ).model_dump()
                
                # Dismiss the pending review
                dismiss_path = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews/{pending_review['id']}/dismissals"
                dismiss_payload = {"message": request.body or "Review dismissed"}
                self.action_executor.client.put(dismiss_path, payload=dismiss_payload)
                
                return ManagePendingReviewResponse(
                    success=True,
                    review_id=pending_review["id"],
                    message="Pending review dismissed"
                ).model_dump()
            
            elif request.action == "add_comment":
                # Add comment to pending review
                if not request.comments:
                    return ManagePendingReviewResponse(
                        success=False,
                        message="No comments provided for add_comment action"
                    ).model_dump()
                
                # Add review comments
                for comment in request.comments:
                    comment_path = f"/repos/{owner}/{repo}/pulls/{pr_number}/comments"
                    self.action_executor.client.post(comment_path, payload=comment)
                
                return ManagePendingReviewResponse(
                    success=True,
                    message=f"Added {len(request.comments)} comments to pending review"
                ).model_dump()
            
            else:
                return ManagePendingReviewResponse(
                    success=False,
                    message=f"Unknown action: {request.action}"
                ).model_dump()
        
        except Exception as e:
            return ManagePendingReviewResponse(
                success=False,
                message=str(e)
            ).model_dump()
    
    async def review_pr(self, params: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive PR review - single entry point."""
        pr_number = params.get("pr_number")
        include_all = params.get("include_all", True)
        
        if not pr_number:
            return {"error": "Missing pr_number parameter"}
        
        # Auto-detect context
        context = self._auto_detect_context()
        if "error" in context:
            return context
        
        result = await self.orchestrator.review_pr(pr_number, context["owner"], context["repo"], include_all)
        return {
            "pr_info": result.pr_info,
            "conversation_analysis": result.conversation_analysis,
            "priority_actions": result.priority_actions,
            "summary": result.summary
        }
    
    async def get_pending_reviews(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get pending reviews with inline comments via GraphQL."""
        pr_number = params.get("pr_number")
        if not pr_number:
            return {"error": "Missing pr_number parameter"}
        
        context = self._auto_detect_context()
        if "error" in context:
            return context
        
        result = await self.graphql_client.get_pending_reviews(
            context["owner"], context["repo"], pr_number
        )
        return result
    
    async def submit_pending_review(self, params: dict[str, Any]) -> dict[str, Any]:
        """Submit pending review via GraphQL."""
        from .pending_reviews_schemas import SubmitPendingReviewRequest
        
        request = SubmitPendingReviewRequest.model_validate(params)
        context = self._auto_detect_context()
        if "error" in context:
            return context
        
        result = await self.graphql_client.submit_pending_review(
            context["owner"], context["repo"], request.pr_number,
            request.review_id, request.event, request.body
        )
        return result

    async def serve_stdio(self) -> None:
        server = JSONRPCServer(self.jsonrpc_handlers(), schemas=self.schemas())
        await server.serve_stdio()

    def schemas(self) -> dict[str, dict[str, Any]]:
        from .pending_reviews_schemas import SubmitPendingReviewRequest
        from .review_schemas import ReviewPRRequest
        return {
            "review_pr": schema_for(ReviewPRRequest),
            "apply_actions": schema_for(ApplyActionsRequest),
            "generate_reply": schema_for(GenerateReplyRequest),
            "get_pending_reviews": {"type": "object", "properties": {"pr_number": {"type": "integer"}}, "required": ["pr_number"]},
            "submit_pending_review": schema_for(SubmitPendingReviewRequest),
            "health": {"type": "object", "properties": {}},
            "set_policy": schema_for(SetPolicyRequest),
        }


async def run_stdio(config: ServerConfig) -> None:
    server = MCPServer.create(config)
    await server.serve_stdio()


__all__ = ["MCPServer", "run_stdio"]