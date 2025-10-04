# Architecture Overview

```
+-----------------+        +---------------------+        +---------------------+
| GitHub Webhooks | -----> | FastAPI Webhook App | -----> | Event Dispatcher    |
+-----------------+        +---------------------+        +----------+----------+
                                                                  |
                                                                  v
                                                      +-----------------------+
                                                      | Triage Engine         |
                                                      |  - Actor Classifier   |
                                                      |  - Policy Evaluation  |
                                                      +-----------+-----------+
                                                                  |
                                             +--------------------+--------------------+
                                             |                                         |
                                             v                                         v
                               +-----------------------+              +-----------------------+
                               | Responder             |              | Action Executor       |
                               |  - Human replies      |              |  - GitHub API writes  |
                               |  - Bot acknowledgements|              |  - Dry-run support    |
                               +-----------+-----------+              +-----------+-----------+
                                           |                                      |
                                           v                                      v
                               +-----------------------+              +-----------------------+
                               | Thread Manager        |              | Storage (SQLite)      |
                               +-----------------------+              +-----------------------+
```

The Model Context Protocol (MCP) server exposes a JSON-RPC interface over stdio for agents and orchestrators. The same business logic powers the webhook ingestion path.

## Components

- **Webhook App** – Receives GitHub events, validates signatures, and hands off for asynchronous processing.
- **Actor Classifier** – Matches bot patterns and caches results to keep per-event latency low.
- **Triage Engine** – Applies policy rules to determine follow-up actions, labels, and assignments.
- **Responder** – Generates tone-appropriate replies with optional code context references.
- **Thread Manager** – Maintains an idempotent mapping between review comments and logical threads stored in SQLite.
- **Action Executor** – Calls the GitHub REST API with retries and rate-limit awareness, honouring dry-run settings when enabled.

## MCP Tools

| Tool | Description |
| ---- | ----------- |
| `classify_actor` | Returns whether the actor is a bot or human based on deterministic rules. |
| `triage_event` | Produces labels and actions for pull request events. |
| `generate_reply` | Creates thread-aware responses tailored to bots or humans. |
| `apply_actions` | Executes GitHub writes with retries and dry-run support. |
| `map_inline_thread` | Persists the mapping of review comments to thread IDs. |
| `set_policy` | Updates the in-memory policy without restarting the server. |
| `health` | Returns version information. |

