# MCP GitHub Review Server

[![CI](https://github.com/KenkoGeek/mcp-gh-code-review/actions/workflows/ci.yml/badge.svg)](https://github.com/KenkoGeek/mcp-gh-code-review/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A production-focused Model Context Protocol (MCP) server for automating GitHub pull request reviews, inline comment threads, and intelligent responses.

## Features

- **5 JSON-RPC Tools** - PR review, inline comment replies, review threads, pending reviews, health checks
- **Webhook Integration** - FastAPI endpoint with GitHub signature verification
- **13 Tests** - Comprehensive test coverage including error handling and security
- **Structured Logging** - JSON logs with rate limit tracking and error context
- **Bot Detection** - Automatic identification of bot accounts with reply guidance

## Quick Start

### Installation

```bash
git clone https://github.com/KenkoGeek/mcp-gh-code-review.git
cd mcp-gh-code-review
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your credentials
```

**Required:**
- `GITHUB_TOKEN` - GitHub personal access token with minimal permissions (see below)

**GitHub Token Permissions:**

*Fine-grained Personal Access Token (Recommended):*
- **Repository permissions:**
  - `pull_requests: write` - Create/update PR comments and reviews
  - `issues: write` - Add comments to PR discussions
  - `metadata: read` - Read basic repository information
  - `contents: read` - Access repository files and structure

*Personal Access Token (Classic):*
- `repo` scope - Full repository access

**Optional:**
- `WEBHOOK_SECRET` - Secret for webhook signature verification

## Usage

### 1. MCP Client Integration

Connect from Claude Desktop, IDEs, or any MCP-compatible client.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "github-review": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "mcp_server.cli", "--stdio"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

**Run standalone:**
```bash
python -m mcp_server.cli --stdio
```

### 2. Webhook Server

Receive and process GitHub webhook events.

**Local development:**
```bash
uvicorn mcp_server.webhooks:app --reload
```

**Production:**
```bash
uvicorn mcp_server.webhooks:app --host 0.0.0.0 --port 8000 --workers 4
```

**GitHub Webhook Configuration:**
- Payload URL: `https://your-domain.com/webhook`
- Content type: `application/json`
- Secret: Set `WEBHOOK_SECRET` in `.env`
- Events: Pull requests, Pull request reviews, Issue comments

### 3. Docker Deployment

**Using pre-built image from GitHub Container Registry:**

```bash
# MCP server
docker run -i \
  -e GITHUB_TOKEN=ghp_xxx \
  ghcr.io/kenkogeek/mcp-gh-code-review:latest

# Webhook server
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e WEBHOOK_SECRET=your_secret \
  ghcr.io/kenkogeek/mcp-gh-code-review:latest \
  uvicorn mcp_server.webhooks:app --host 0.0.0.0
```

**Build locally:**

```bash
docker build -t mcp-gh-review .

# Run MCP server
docker run -i -e GITHUB_TOKEN=ghp_xxx mcp-gh-review

# Run webhook server
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e WEBHOOK_SECRET=your_secret \
  mcp-gh-review \
  uvicorn mcp_server.webhooks:app --host 0.0.0.0
```

## Available Tools

| Tool | Description |
|------|-------------|
| `review_pr` | Comprehensive PR analysis with reviews, comments, and threads |
| `reply_to_comment` | Reply to inline PR comments using databaseId |
| `get_review_threads` | Get review threads with isResolved status via GraphQL |
| `submit_pending_review` | Submit pending reviews with specified event type |
| `health` | Check server status and GitHub API rate limits |



## Development

### Testing

```bash
pip install -e .[dev]
pytest
pytest --cov=mcp_server  # With coverage
```

### Linting

```bash
ruff check src/
mypy src/
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed component diagrams and data flow.

```
GitHub Webhooks → FastAPI → MCP Server → GitHub REST/GraphQL APIs
```

## Monitoring

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "database_healthy": true,
  "rate_limit": {
    "remaining": 4850,
    "reset": 1234567890
  }
}
```

**Structured Logs:**
- All operations logged with `structlog`
- JSON format for easy parsing
- Includes context: event IDs, actors, actions

## Security

- **Webhook Verification** - `X-Hub-Signature-256` HMAC validation
- **Token Security** - Never logged, use environment variables or secret managers
- **Non-root Container** - Docker runs as unprivileged `app` user
- **Input Validation** - Pydantic models validate all inputs
- **Rate Limit Tracking** - Monitors GitHub API limits

## Troubleshooting

### Rate Limit Issues

**Check current limits:**
```bash
curl http://localhost:8000/health | jq .rate_limit
```

**Solutions:**
- Use GitHub App for higher limits (5000/hour vs 60/hour)
- Enable conditional requests with ETags
- Implement request caching

### Authentication Errors

**401 Unauthorized:**
```bash
# Verify token has required permissions
gh auth status
# Regenerate token if expired
```

**403 Forbidden:**
- Check repository access permissions
- Verify token scopes include `repo` or fine-grained permissions
- Ensure not hitting secondary rate limits

### Webhook Issues

**Signature verification fails:**
```bash
# Verify WEBHOOK_SECRET matches GitHub configuration
echo $WEBHOOK_SECRET
# Check webhook delivery logs in GitHub settings
```

**Payload validation errors:**
- Ensure webhook sends `application/json` content type
- Verify payload includes required `action` field
- Check GitHub webhook delivery response for details

### Connection Errors

**Network timeouts:**
```bash
# Test GitHub API connectivity
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

**Solutions:**
- Check firewall/proxy settings
- Verify DNS resolution for api.github.com
- Enable retry logic (already implemented for network errors)

### Logging and Debugging

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
python -m mcp_server.cli --stdio
```

**View structured logs:**
```bash
# Logs output to stderr in JSON format
python -m mcp_server.cli --stdio 2> debug.log
jq . debug.log  # Pretty print JSON logs
```

**Common log events:**
- `github_api_request` - API calls with method, path, status
- `review_pr_start` / `review_pr_complete` - Tool invocations
- `error` - Failures with context and GitHub error messages

## Contributing

[Check here](CONTRIBUTING.md)

## License

MIT License - See [LICENSE](LICENSE) for details.
