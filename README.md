# MCP GitHub Review Server

[![CI](https://github.com/KenkoGeek/mcp-gh-code-review/actions/workflows/ci-release.yml/badge.svg)](https://github.com/KenkoGeek/mcp-gh-code-review/actions/workflows/ci-release.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A Model Context Protocol (MCP) server that automates GitHub pull request and issue workflows for MCP-compatible clients.

## Overview

- 8 JSON-RPC tools for reviewing pull requests, inspecting issues, replying inline, and performing health checks
- GitHub REST and GraphQL integrations with retry logic and rate limit tracking
- Optional FastAPI webhook endpoint with HMAC signature validation
- Structured JSON logging via `structlog` with configurable verbosity
- Lightweight bot detection to tailor responses for automated users

## Requirements

- Python 3.11 or later
- A GitHub personal access token (fine-grained or classic) with at least:
  - `pull_requests:write`, `issues:write`, `metadata:read`, `contents:read` (fine-grained)
  - or the `repo` scope (classic tokens)
- Optional: `WEBHOOK_SECRET` to secure webhook deliveries

The server can detect the target repository from the current git remote. If you are not running inside a clone, set `GITHUB_REPOSITORY=owner/repo`.

## Installation

### Run with uvx (recommended)

```bash
uvx --from git+https://github.com/KenkoGeek/mcp-gh-code-review mcp-gh-review
```

### Local development install

```bash
git clone https://github.com/KenkoGeek/mcp-gh-code-review.git
cd mcp-gh-code-review
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Docker

```bash
docker build -t mcp-gh-review .
docker run --rm -it \
  -e GITHUB_TOKEN=ghp_your_token \
  -e GITHUB_REPOSITORY=owner/repo \
  mcp-gh-review
```

## Configuration

Set the following environment variables before launching the server:

- `GITHUB_TOKEN` (required) – GitHub authentication token
- `GITHUB_REPOSITORY` (optional) – fallback repo in `owner/repo` format
- `LOG_LEVEL` (optional) – `DEBUG`, `INFO`, `WARNING`, or `ERROR` (default: `INFO`)
- `WEBHOOK_SECRET` (optional) – shared secret for webhook signature verification

## Usage

### Run as an MCP server (stdio)

```bash
mcp-gh-review
```

The entry point configures structured logging and starts a JSON-RPC 2.0 loop over stdio. Any MCP-compatible client can connect, request the tool list, and invoke the actions.

#### Example Claude Desktop configuration

Add the following snippet to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github-review": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/KenkoGeek/mcp-gh-code-review",
        "mcp-gh-review"
      ],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here",
        "GITHUB_REPOSITORY": "owner/repo"
      }
    }
  }
}
```

### Available MCP tools

| Tool | Description |
| --- | --- |
| `review_pr` | Fetches PR metadata, reviews, and review threads (via REST + GraphQL) and annotates comments with bot/user markers. |
| `reply_to_comment` | Replies to a specific inline review comment using its database ID. |
| `get_review_threads` | Retrieves review threads with `isResolved` status. |
| `submit_pending_review` | Submits a pending review using the GraphQL API. |
| `list_issues` | Lists repository issues (excluding pull requests) in the requested state. |
| `review_issue` | Returns issue details and comments with bot detection hints. |
| `reply_to_issue_comment` | Creates a new issue comment reply. |
| `health` | Returns basic health information and current REST API rate limits. |

Each tool exposes a JSON schema describing the expected input parameters, which MCP clients can use for validation and UI generation.

### Optional webhook endpoint

The project also provides a minimal FastAPI application that validates HMAC signatures and accepts GitHub webhook payloads.

```bash
uvicorn mcp_server.webhooks:app --reload
```

When `WEBHOOK_SECRET` is configured, webhook deliveries must include the `X-Hub-Signature-256` header.

### Health check

```bash
curl http://localhost:8000/health
```

The response includes the cached REST API rate limit counters maintained by the MCP tools.

## Logging

Logging is handled by `structlog` and emitted as JSON to stderr. Adjust verbosity with `LOG_LEVEL=DEBUG` for troubleshooting. REST and GraphQL interactions include context such as method, path, status, and remaining rate limit.

## Development

```bash
pip install -e .[dev]
pytest
pytest --cov
ruff check src/
mypy src/
```

- Tests cover the GitHub client, error handling, JSON-RPC routing, and webhook validation.
- `pytest-asyncio` powers asynchronous server tests.
- `ruff` and `mypy` keep the codebase linted and typed.

See `docs/architecture.md` for a component overview and data flow diagram.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidance on setting up your environment, running checks, and submitting pull requests.

## License

MIT License – see [LICENSE](LICENSE) for details.
