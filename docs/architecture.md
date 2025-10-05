# Architecture Overview

```
+-----------------+        +---------------------+        +---------------------+
| GitHub Webhooks | -----> | FastAPI Webhook App | -----> | Event Dispatcher    |
+-----------------+        +---------------------+        +----------+----------+
                                                                  |
                                                                  v
                                                      +-----------------------+
                                                      | PR Orchestrator       |
                                                      |  - Data Fetching      |
                                                      |  - Thread Analysis    |
                                                      |  - Triage & Actions   |
                                                      +-----------+-----------+
                                                                  |
                                             +--------------------+--------------------+
                                             |                    |                    |
                                             v                    v                    v
                               +-----------------------+  +---------------+  +------------------+
                               | GitHub REST API       |  | GraphQL API   |  | Thread Analyzer  |
                               |  - PR data            |  | - Pending     |  | - Conversation   |
                               |  - Comments/Reviews   |  |   reviews     |  |   context        |
                               +-----------+-----------+  +-------+-------+  +--------+---------+
                                           |                      |                   |
                                           v                      v                   v
                               +-----------------------+              +-----------------------+
                               | Action Executor       |              | Storage (SQLite)      |
                               |  - GitHub API writes  |              |  - Thread mappings    |
                               |  - Dry-run support    |              |  - Health checks      |
                               +-----------------------+              +-----------------------+
```

The Model Context Protocol (MCP) server exposes a JSON-RPC interface over stdio for agents and orchestrators. The same business logic powers the webhook ingestion path.

## Components

- **PR Orchestrator** – Single entry point that coordinates comprehensive PR analysis, data fetching, and action prioritization.
- **GitHub REST Client** – Fetches PR data, reviews, comments with connection reuse and rate limit tracking.
- **GraphQL Client** – Accesses pending review content not available via REST API.
- **Thread Analyzer** – Analyzes conversation threads to identify responses needed and prevent inappropriate replies.
- **Triage Engine** – Applies policy rules to determine follow-up actions, labels, and assignments.
- **Action Executor** – Executes GitHub API writes with retries, validation, and dry-run support.
- **Thread Manager** – Maintains idempotent mapping between review comments and logical threads in SQLite.
- **Actor Classifier** – Deterministic bot detection with configurable patterns and caching.

## MCP Tools

| Tool | Description |
| ---- | ----------- |
| `review_pr` | **Primary entry point** - Comprehensive PR analysis with conversation threads and priority actions |
| `apply_actions` | Execute GitHub API actions (comment, label, assign) with dry-run support |
| `generate_reply` | Create context-aware responses for comment threads |
| `get_pending_reviews` | Retrieve pending reviews with inline comments via GraphQL |
| `submit_pending_review` | Submit pending reviews with specified event type |
| `set_policy` | Update triage policy at runtime |
| `health` | Check server status, database, and rate limits |

