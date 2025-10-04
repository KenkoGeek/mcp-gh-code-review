"""Command line entry point for the MCP server."""

from __future__ import annotations

import argparse
import asyncio
import os

from .config import load_from_env
from .server import run_stdio


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MCP GitHub review server")
    parser.add_argument("--stdio", action="store_true", help="Run the MCP server over stdio")
    args = parser.parse_args()
    config = load_from_env(os.environ)
    if args.stdio:
        asyncio.run(run_stdio(config))
    else:
        parser.error("Only --stdio mode is currently supported")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
