"""Actor classifier used to distinguish humans from bots."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from cachetools import TTLCache


@dataclass(slots=True)
class Classification:
    actor_type: str
    reason: str
    matched_rule: str | None = None


class ActorClassifier:
    """Deterministic classifier for actors."""

    def __init__(self, bot_patterns: Iterable[str], ttl_seconds: int = 300) -> None:
        self._patterns: list[re.Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE) for pattern in bot_patterns
        ]
        self._cache: TTLCache[str, Classification] = TTLCache(maxsize=1024, ttl=ttl_seconds)

    def classify(self, login: str, name: str | None = None) -> Classification:
        cache_key = f"{login}:{name or ''}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        normalized = login.lower()
        if normalized.endswith("[bot]"):
            result = Classification(actor_type="bot", reason="[bot] suffix", matched_rule="suffix")
        elif normalized.endswith("-bot"):
            result = Classification(actor_type="bot", reason="-bot suffix", matched_rule="suffix")
        else:
            matched_pattern = None
            for pattern in self._patterns:
                if pattern.search(login):
                    matched_pattern = pattern.pattern
                    break
            if matched_pattern:
                result = Classification(
                    actor_type="bot", reason="matched configured pattern", matched_rule=matched_pattern
                )
            elif name:
                for pattern in self._patterns:
                    if pattern.search(name):
                        matched_pattern = pattern.pattern
                        break
                if matched_pattern:
                    result = Classification(
                        actor_type="bot", reason="matched name pattern", matched_rule=matched_pattern
                    )
                else:
                    result = Classification(actor_type="human", reason="no bot pattern matched")
            else:
                result = Classification(actor_type="human", reason="no bot pattern matched")
        self._cache[cache_key] = result
        return result


__all__ = ["ActorClassifier", "Classification"]
