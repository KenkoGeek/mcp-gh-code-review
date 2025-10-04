"""Configuration loading for the MCP server."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class GitHubConfig:
    """GitHub authentication configuration."""

    app_id: int | None = None
    private_key: str | None = None
    installation_id: int | None = None
    token: str | None = None


@dataclass(slots=True)
class ServerConfig:
    """Top level configuration for the MCP server."""

    github: GitHubConfig = field(default_factory=GitHubConfig)
    bot_actors: list[str] = field(default_factory=list)
    dry_run: bool = False
    policy_path: Path | None = None
    log_level: str = "INFO"


@dataclass(slots=True)
class PolicyConfig:
    """Configuration for routing and triage policies."""

    labels: Mapping[str, list[str]] = field(default_factory=dict)
    owners: Mapping[str, list[str]] = field(default_factory=dict)
    auto_approve_paths: list[str] = field(default_factory=list)
    protected_paths: Mapping[str, list[str]] = field(default_factory=dict)
    sla_hours: int = 24


DEFAULT_BOT_PATTERNS = [
    "dependabot[bot]",
    "github-actions[bot]",
    "renovate[bot]",
    "snyk-bot",
    "semantic-release-bot",
    "codecov[bot]",
    "trivy-bot",
    "amazon-q",
    "cursor",
    "copilot",
    "openai-codex",
    "aider",
    "sweep-ai",
    "codiumai",
    "sonarqube",
    "codeql",
]


def load_policy(path: Path) -> PolicyConfig:
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    if not isinstance(data, MutableMapping):  # pragma: no cover - defensive
        raise ValueError("Policy file must contain a mapping")
    labels = {str(k): list(v) for k, v in data.get("labels", {}).items()}
    owners = {str(k): list(v) for k, v in data.get("owners", {}).items()}
    auto = list(data.get("auto_approve_paths", []))
    protected = {str(k): list(v) for k, v in data.get("protected_paths", {}).items()}
    sla_hours = int(data.get("sla_hours", 24))
    return PolicyConfig(
        labels=labels,
        owners=owners,
        auto_approve_paths=auto,
        protected_paths=protected,
        sla_hours=sla_hours,
    )


def load_from_env(env: Mapping[str, str]) -> ServerConfig:
    github = GitHubConfig(
        app_id=int(env["GITHUB_APP_ID"]) if env.get("GITHUB_APP_ID") else None,
        private_key=env.get("GITHUB_PRIVATE_KEY"),
        installation_id=(
            int(env["GITHUB_INSTALLATION_ID"])
            if env.get("GITHUB_INSTALLATION_ID")
            else None
        ),
        token=env.get("GITHUB_TOKEN"),
    )
    patterns = list(DEFAULT_BOT_PATTERNS)
    if env.get("BOT_ACTORS"):
        patterns.extend(x.strip() for x in env["BOT_ACTORS"].split(",") if x.strip())
    policy_path = Path(env["POLICY_PATH"]) if env.get("POLICY_PATH") else None
    dry_run = env.get("DRY_RUN", "false").lower() in {"1", "true", "yes"}
    log_level = env.get("LOG_LEVEL", "INFO")
    return ServerConfig(
        github=github,
        bot_actors=patterns,
        dry_run=dry_run,
        policy_path=policy_path,
        log_level=log_level,
    )


def merge_policy(base: PolicyConfig, override: PolicyConfig | None) -> PolicyConfig:
    if override is None:
        return base
    labels: dict[str, list[str]] = {**base.labels}
    for key, values in override.labels.items():
        labels.setdefault(key, []).extend(values)
    owners: dict[str, list[str]] = {**base.owners}
    for key, values in override.owners.items():
        owners.setdefault(key, []).extend(values)
    protected: dict[str, list[str]] = {**base.protected_paths}
    for key, values in override.protected_paths.items():
        protected.setdefault(key, []).extend(values)
    auto = list(base.auto_approve_paths)
    auto.extend(override.auto_approve_paths)
    sla = override.sla_hours or base.sla_hours
    return PolicyConfig(
        labels=labels,
        owners=owners,
        protected_paths=protected,
        auto_approve_paths=auto,
        sla_hours=sla,
    )
