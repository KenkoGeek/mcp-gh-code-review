"""PR review orchestration - single entry point for comprehensive PR analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PRReviewResult:
    pr_info: dict[str, Any]
    conversation_analysis: dict[str, Any]
    priority_actions: list[dict[str, Any]]
    summary: dict[str, Any]


class PROrchestrator:
    """Orchestrate complete PR review workflow."""
    
    def __init__(self, server):
        self.server = server
    
    async def review_pr(self, pr_number: int, owner: str, repo: str, include_all: bool = True) -> PRReviewResult:
        """Complete PR review workflow - single entry point."""
        
        # 1. Get comprehensive PR data
        pr_data = await self.server.get_pr_data({
            "pr_number": pr_number,
            "include": ["info", "reviews", "comments", "inline_comments", "pending_reviews"] if include_all else ["info"]
        })
        
        if "error" in pr_data:
            return PRReviewResult(
                pr_info={},
                conversation_analysis={"error": pr_data["error"]},
                priority_actions=[],
                summary={"error": pr_data["error"]}
            )
        
        # 2. Analyze conversations and priorities
        analysis = await self.server.analyze_pr_reviews({"pr_number": pr_number})
        
        # 3. Run triage on all events
        triage_results = await self._run_triage(pr_data, analysis)
        
        # 4. Generate priority actions (including triage)
        priority_actions = self._generate_priority_actions(analysis, triage_results, pr_number)
        
        # 5. Create summary
        summary = self._create_summary(pr_data, analysis, triage_results)
        
        return PRReviewResult(
            pr_info=pr_data.get("pr_info", {}),
            conversation_analysis=analysis,
            priority_actions=priority_actions,
            summary=summary
        )
    
    async def _run_triage(self, pr_data: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
        """Run triage on all PR events."""
        triage_results = {
            "suggested_labels": [],
            "suggested_assignments": [],
            "automated_actions": []
        }
        
        # Triage based on PR state and conversations
        threads_needing_response = analysis.get("summary", {}).get("threads_needing_response", 0)
        
        # Auto-label based on status
        if threads_needing_response > 0:
            triage_results["suggested_labels"].append("needs-response")
        
        # Auto-label based on review state
        reviews = pr_data.get("reviews", [])
        if any(r.get("state") == "CHANGES_REQUESTED" for r in reviews):
            triage_results["suggested_labels"].append("needs-changes")
        elif any(r.get("state") == "APPROVED" for r in reviews):
            triage_results["suggested_labels"].append("approved")
        
        return triage_results
    
    def _generate_priority_actions(self, analysis: dict[str, Any], triage_results: dict[str, Any], pr_number: int) -> list[dict[str, Any]]:
        """Generate suggested actions based on analysis."""
        actions = []
        
        # Priority responses needed
        for response in analysis.get("priority_responses", []):
            actions.append({
                "type": "respond_to_comment",
                "priority": "high",
                "comment_id": response["comment_id"],
                "path": response["path"],
                "line": response["line"],
                "participants": response["participants"],
                "suggested_action": {
                    "type": "comment",
                    "metadata": {"pr_number": pr_number, "in_reply_to": str(response["comment_id"])}
                }
            })
        
        # Triage actions
        for label in triage_results.get("suggested_labels", []):
            actions.append({
                "type": "apply_label",
                "priority": "low",
                "label": label,
                "suggested_action": {
                    "type": "apply_label",
                    "value": label,
                    "metadata": {"pr_number": pr_number}
                }
            })
        
        # Pending reviews to submit
        pending_count = analysis.get("summary", {}).get("threads_needing_response", 0)
        if pending_count > 0:
            actions.append({
                "type": "pending_reviews_detected",
                "priority": "medium",
                "count": pending_count,
                "suggested_action": {
                    "type": "review_pending_comments",
                    "description": f"{pending_count} conversation threads need responses"
                }
            })
        
        return actions
    
    def _create_summary(self, pr_data: dict[str, Any], analysis: dict[str, Any], triage_results: dict[str, Any]) -> dict[str, Any]:
        """Create executive summary of PR status."""
        pr_info = pr_data.get("pr_info", {})
        summary_data = analysis.get("summary", {})
        
        return {
            "pr_number": pr_info.get("number"),
            "title": pr_info.get("title"),
            "state": pr_info.get("state"),
            "author": pr_info.get("user", {}).get("login"),
            "total_reviews": summary_data.get("total_reviews", 0),
            "total_inline_comments": summary_data.get("total_inline_comments", 0),
            "conversation_threads": summary_data.get("conversation_threads", 0),
            "threads_needing_response": summary_data.get("threads_needing_response", 0),
            "pending_reviews": pr_data.get("pending_reviews", {}).get("count", 0),
            "suggested_labels": triage_results.get("suggested_labels", []),
            "status": self._determine_status(summary_data, pr_data),
            "next_action": self._suggest_next_action(summary_data, pr_data)
        }
    
    def _determine_status(self, summary: dict[str, Any], pr_data: dict[str, Any]) -> str:
        """Determine overall PR status."""
        threads_needing_response = summary.get("threads_needing_response", 0)
        pending_reviews = pr_data.get("pending_reviews", {}).get("count", 0)
        
        if threads_needing_response > 0:
            return "needs_responses"
        elif pending_reviews > 0:
            return "has_pending_reviews"
        else:
            return "up_to_date"
    
    def _suggest_next_action(self, summary: dict[str, Any], pr_data: dict[str, Any]) -> str:
        """Suggest next action for user."""
        threads_needing_response = summary.get("threads_needing_response", 0)
        pending_reviews = pr_data.get("pending_reviews", {}).get("count", 0)
        
        if threads_needing_response > 0:
            return f"Respond to {threads_needing_response} conversation threads"
        elif pending_reviews > 0:
            return f"Submit {pending_reviews} pending reviews"
        else:
            return "No immediate actions needed"


__all__ = ["PROrchestrator", "PRReviewResult"]