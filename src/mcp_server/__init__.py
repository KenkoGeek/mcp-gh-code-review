"""MCP GitHub review server."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-github-review-server")
except PackageNotFoundError:  # pragma: no cover - during local dev
    __version__ = "0.1.0"

__all__ = ["__version__"]
