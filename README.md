# MCP GitHub Review Server

A production-focused Model Context Protocol (MCP) server for automating GitHub pull request reviews, inline comment threads, and intelligent responses.

## Features

- **7 JSON-RPC Tools** - Comprehensive PR review, pending review management, apply actions, generate replies, health checks, policy updates
- **Bot Detection** - Deterministic classifier with configurable patterns and caching
- **Webhook Integration** - FastAPI endpoint with GitHub signature verification
- **Idempotent Storage** - SQLite-backed thread mappings for retry safety
- **Policy Engine** - YAML-driven triage rules for labels, assignments, and automation
- **Production Ready** - Structured logging, error handling, rate limit tracking, dry-run mode
- **Modern Python** - Uses match/case patterns, type hints, and Python 3.10+ features
- **Comprehensive Tests** - 14 tests covering all core functionality

## Quick Start

### Installation

```bash
git clone <repository-url>
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
- `GITHUB_TOKEN` - GitHub personal access token or app credentials

**Optional:**
- `BOT_ACTORS` - Comma-separated bot patterns (extends defaults)
- `POLICY_PATH` - Path to policy YAML file (default: none)
- `DB_PATH` - SQLite database path (default: `.mcp/threads.db`)
- `DRY_RUN` - Test mode without GitHub writes (default: `false`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
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
        "GITHUB_TOKEN": "ghp_your_token_here",
        "POLICY_PATH": "/path/to/policy.yaml"
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
  -e POLICY_PATH=/app/config/policy.yaml \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/data \
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
| `review_pr` | Comprehensive PR analysis with conversation threads and priority actions |
| `get_pending_reviews` | Retrieve pending reviews with inline comments via GraphQL |
| `submit_pending_review` | Submit pending reviews with specified event type |
| `apply_actions` | Execute GitHub API actions (comment, label, assign) |
| `generate_reply` | Create context-aware responses for comments |
| `set_policy` | Update triage policy at runtime |
| `health` | Check server status, database, and rate limits |

## Policy Configuration

Create `config/policy.yaml` to define triage rules:

```yaml
# Auto-label based on file paths
labels:
  src/frontend/: [frontend, ui]
  src/backend/: [backend, api]
  tests/: [testing]
  docs/: [documentation]

# Auto-assign reviewers by path
owners:
  src/auth/: [security-team]
  src/database/: [db-team]

# Paths that can be auto-approved
auto_approve_paths:
  - docs/
  - README.md
  - "*.md"

# Protected paths requiring specific reviewers
protected_paths:
  src/security/: [security-lead]
  config/production/: [ops-team]

# SLA for review responses (hours)
sla_hours: 24
```

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
GitHub Webhooks → FastAPI → Triage Engine → Responder/Actions → Storage
                              ↓
                    Actor Classifier + Policy
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

**Database locked errors:**
```bash
# Check database path permissions
ls -la .mcp/threads.db
# Set DB_PATH to writable location
export DB_PATH=/tmp/threads.db
```

**Rate limit exceeded:**
```bash
# Check current limits
curl http://localhost:8000/health | jq .rate_limit
# Use GitHub App for higher limits (5000/hour)
```

**Dry-run mode:**
```bash
# Test without making GitHub API calls
export DRY_RUN=true
python -m mcp_server.cli --stdio
```

## Contributing

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for recent enhancements.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) for details.
