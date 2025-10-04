# MCP GitHub Review Server

This repository implements a production-focused Model Context Protocol (MCP) server for managing GitHub pull request reviews, inline comment threads, and automated responses.

## Features

- JSON-RPC tools that classify actors, triage events, generate replies, apply GitHub actions, and manage inline comment threads.
- Deterministic bot classifier with configurable patterns and caching.
- FastAPI webhook endpoint with signature verification.
- SQLite-backed storage for thread mappings to ensure idempotent replies on retries.
- Policy-driven triage engine to assign labels and automate follow-up actions.
- Structured logging, dry-run support, and retry-safe GitHub interactions.
- Comprehensive tests covering classifier behaviour, triage routing, responder output, GitHub action execution, and thread mapping.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Create a `.env` file with your GitHub credentials, or export the following environment variables:

- `GITHUB_TOKEN`
- `BOT_ACTORS`
- `POLICY_PATH`
- `DRY_RUN`
- `LOG_LEVEL`

To run the MCP server over stdio:

```bash
python -m mcp_server.cli --stdio
```

To expose the webhook service locally:

```bash
uvicorn mcp_server.webhooks:app --reload
```

## Testing

```bash
pytest
```

## Tool Schemas

Each MCP tool exposes JSON Schema definitions to simplify integration. See `mcp_server/schemas.py` for authoritative models.

## Security Notes

- Webhook requests require an `X-Hub-Signature-256` header and are verified with the configured secret.
- Secrets should be provided via environment variables or a secret manager. They are never logged.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
