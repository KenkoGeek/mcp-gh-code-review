"""CLI entry point."""

from __future__ import annotations

import asyncio
import os

from .logging_config import configure_logging
from .server import run_stdio


def main() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    configure_logging(log_level)
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
