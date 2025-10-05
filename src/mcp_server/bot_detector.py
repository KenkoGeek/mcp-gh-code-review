"""Bot detection for GitHub actors."""

from __future__ import annotations

BOT_PATTERNS = [
    "[bot]",
    "-bot",
    "bot-",
    "dependabot",
    "renovate",
    "github-actions",
    "codecov",
    "sonarcloud",
]


def is_bot(login: str) -> bool:
    """Detect if GitHub login is a bot."""
    login_lower = login.lower()
    return any(pattern in login_lower for pattern in BOT_PATTERNS)


__all__ = ["is_bot"]
