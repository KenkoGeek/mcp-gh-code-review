# Architecture Overview

```
+-----------------+        +---------------------+        +---------------------+
| GitHub Webhooks | -----> | FastAPI Webhook App | -----> | MCP Server          |
+-----------------+        +---------------------+        +----------+----------+
                                                                  |
                                                                  v
                                                      +-----------------------+
                                                      | MCP Tools (5)         |
                                                      |  - review_pr          |
                                                      |  - reply_to_comment   |
                                                      |  - get_review_threads |
                                                      |  - submit_pending     |
                                                      |  - health             |
                                                      +-----------+-----------+
                                                                  |
                                             +--------------------+--------------------+
                                             |                                         |
                                             v                                         v
                               +-----------------------+                  +-----------------------+
                               | GitHub REST API       |                  | GraphQL API           |
                               |  - PR data            |                  |  - reviewThreads      |
                               |  - Comments/Reviews   |                  |    (isResolved)       |
                               |  - Reply to comments  |                  |  - Pending reviews    |
                               +-----------------------+                  +-----------------------+
```

The Model Context Protocol (MCP) server exposes a JSON-RPC interface over stdio for agents and orchestrators.

## Components

- **MCP Server** – JSON-RPC server with 5 tools for PR review automation
- **GitHub REST Client** – Fetches PR data, reviews, comments; posts replies with `databaseId`
- **GraphQL Client** – Accesses `reviewThreads` with `isResolved` status and pending reviews
- **Webhooks** – FastAPI endpoint with GitHub signature verification

## MCP Tools

| Tool | Description |
| ---- | ----------- |
| `review_pr` | Comprehensive PR analysis with reviews, comments, and files changed |
| `reply_to_comment` | Reply to inline PR comments using `databaseId` |
| `get_review_threads` | Get review threads with `isResolved` status via GraphQL |
| `submit_pending_review` | Submit pending reviews with specified event type |
| `health` | Check server status and GitHub API rate limits |

## API Usage

**REST API** – PR data, reviews, comments, replies
**GraphQL API** – `reviewThreads` (for `isResolved`), pending reviews

**Critical**: Inline comment replies require `databaseId` (integer) not GraphQL `id` (string)
