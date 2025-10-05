"""Thread conversation analysis for smart comment prioritization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ThreadParticipant:
    login: str
    is_bot: bool
    is_owner: bool
    comment_count: int
    last_comment_at: datetime


@dataclass(slots=True)
class ConversationThread:
    thread_id: str
    path: str
    line: int
    participants: list[ThreadParticipant]
    total_comments: int
    last_activity: datetime
    needs_response: bool
    last_external_comment_id: str | None
    our_last_response_id: str | None


class ThreadAnalyzer:
    """Analyze comment threads to prioritize responses intelligently."""
    
    def __init__(self, bot_patterns: list[str], authenticated_user: str):
        self.bot_patterns = bot_patterns
        self.authenticated_user = authenticated_user
    
    def analyze_threads(self, inline_comments: list[dict[str, Any]]) -> list[ConversationThread]:
        """Group comments into threads and analyze conversation state."""
        threads: dict[str, list[dict]] = {}
        
        # Group by thread (path:line or in_reply_to chain)
        for comment in inline_comments:
            thread_key = self._get_thread_key(comment, inline_comments)
            if thread_key not in threads:
                threads[thread_key] = []
            threads[thread_key].append(comment)
        
        # Analyze each thread
        analyzed = []
        for thread_key, comments in threads.items():
            thread = self._analyze_thread(thread_key, comments)
            analyzed.append(thread)
        
        # Sort by priority: needs_response first, then by last_activity
        return sorted(analyzed, key=lambda t: (not t.needs_response, t.last_activity), reverse=True)
    
    def _get_thread_key(self, comment: dict, all_comments: list[dict]) -> str:
        """Get thread identifier for grouping related comments."""
        # If it's a reply, find the root comment
        if comment.get("in_reply_to_id"):
            root = self._find_root_comment(comment, all_comments)
            return f"{root.get('path', 'unknown')}:{root.get('line', 0)}:{root['id']}"
        
        # Root comment
        return f"{comment.get('path', 'unknown')}:{comment.get('line', 0)}:{comment['id']}"
    
    def _find_root_comment(self, comment: dict, all_comments: list[dict]) -> dict:
        """Find the root comment of a reply chain."""
        if not comment.get("in_reply_to_id"):
            return comment
        
        parent = next((c for c in all_comments if c["id"] == comment["in_reply_to_id"]), None)
        if parent:
            return self._find_root_comment(parent, all_comments)
        return comment
    
    def _analyze_thread(self, thread_key: str, comments: list[dict]) -> ConversationThread:
        """Analyze a single conversation thread."""
        # Sort by creation time
        comments.sort(key=lambda c: c.get("created_at", ""))
        
        # Extract thread info
        first_comment = comments[0]
        path = first_comment.get("path", "unknown")
        line = first_comment.get("line", 0)
        thread_id = thread_key
        
        # Analyze participants
        participants = self._analyze_participants(comments)
        
        # Determine if needs response
        last_comment = comments[-1]
        last_author = last_comment["user"]["login"]
        
        # Find our last response and last external comment
        our_last_response = None
        last_external_comment = None
        
        for comment in reversed(comments):
            author = comment["user"]["login"]
            if self._is_our_response(author) and not our_last_response:
                our_last_response = comment
            elif not self._is_our_response(author) and not last_external_comment:
                last_external_comment = comment
        
        # Need response if last comment is from external user and we haven't responded to it
        needs_response = (
            not self._is_our_response(last_author) and
            (not our_last_response or 
             (last_external_comment and 
              last_external_comment["created_at"] > our_last_response.get("created_at", "")))
        )
        
        return ConversationThread(
            thread_id=thread_id,
            path=path,
            line=line,
            participants=participants,
            total_comments=len(comments),
            last_activity=datetime.fromisoformat(last_comment["created_at"].replace("Z", "+00:00")),
            needs_response=needs_response,
            last_external_comment_id=last_external_comment["id"] if last_external_comment else None,
            our_last_response_id=our_last_response["id"] if our_last_response else None
        )
    
    def _analyze_participants(self, comments: list[dict]) -> list[ThreadParticipant]:
        """Analyze participants in a thread."""
        participant_data: dict[str, dict] = {}
        
        for comment in comments:
            login = comment["user"]["login"]
            created_at = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
            
            if login not in participant_data:
                participant_data[login] = {
                    "login": login,
                    "is_bot": self._is_bot(login),
                    "is_owner": login == self.authenticated_user,
                    "comment_count": 0,
                    "last_comment_at": created_at
                }
            
            participant_data[login]["comment_count"] += 1
            if created_at > participant_data[login]["last_comment_at"]:
                participant_data[login]["last_comment_at"] = created_at
        
        return [
            ThreadParticipant(**data) 
            for data in participant_data.values()
        ]
    
    def _is_bot(self, login: str) -> bool:
        """Check if user is a bot."""
        return any(pattern in login.lower() for pattern in self.bot_patterns)
    
    def _is_our_response(self, login: str) -> bool:
        """Check if comment is from us (only authenticated user, not bots)."""
        return login == self.authenticated_user
    
    def get_priority_threads(
        self, threads: list[ConversationThread], limit: int = 5
    ) -> list[ConversationThread]:
        """Get threads that need immediate attention."""
        return [t for t in threads if t.needs_response][:limit]


__all__ = ["ThreadAnalyzer", "ConversationThread", "ThreadParticipant"]