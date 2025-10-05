# MCP GitHub Review Server

A production-focused Model Context Protocol (MCP) server for automating GitHub pull request reviews, inline comment threads, and intelligent responses.

## Features

- **5 JSON-RPC Tools** - PR review, inline comment replies, review threads, pending reviews, health checks
- **Webhook Integration** - FastAPI endpoint with GitHub signature verification
- **Minimal Tests** - 3 tests covering core functionality

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

**Build:**
```bash
docker build -t mcp-gh-review .
```

**Run MCP server:**
```bash
docker run -i \
  -e GITHUB_TOKEN=ghp_xxx \
  mcp-gh-review
```

**Run webhook server:**
```bash
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

**Rate limit exceeded:**
```bash
# Check current limits
curl http://localhost:8000/health | jq .rate_limit
# Use GitHub App for higher limits (5000/hour)
```

## Contributing

[Check here](CONTRIBUTING.md)

## License

MIT License - See [LICENSE](LICENSE) for details.
