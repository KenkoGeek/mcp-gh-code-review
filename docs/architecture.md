# Architecture Overview

```
+-----------------+        +---------------------+        +---------------------+
| GitHub Webhooks | -----> | FastAPI Webhook App | -----> | MCP Server          |
+-----------------+        +---------------------+        +----------+----------+
                                                                  |
                                                                  v
                                                      +-----------------------+
                                                      | MCP Tools (8)         |
                                                      | PR Tools:             |
                                                      |  - review_pr          |
                                                      |  - reply_to_comment   |
                                                      |  - get_review_threads |
                                                      |  - submit_pending     |
                                                      | Issue Tools:          |
                                                      |  - list_issues        |
                                                      |  - review_issue       |
                                                      |  - reply_to_issue     |
                                                      | System:               |
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

- **MCP Server** – JSON-RPC server with 8 tools for PR review and issue management
- **GitHub REST Client** – Fetches PR/issue data, reviews, comments; posts replies with `databaseId`
- **GraphQL Client** – Accesses `reviewThreads` with `isResolved` status and pending reviews
- **Webhooks** – FastAPI endpoint with GitHub signature verification
- **Bot Detection** – Identifies bot accounts and annotates comments with `is_bot` flag
- **User Detection** – Identifies authenticated user and annotates with `is_me` flag

## MCP Tools

### Pull Request Tools (5)
| Tool | Description |
| ---- | ----------- |
| `review_pr` | Comprehensive PR analysis with reviews, comments, and threads |
| `reply_to_comment` | Reply to inline PR comments using `databaseId` |
| `get_review_threads` | Get review threads with `isResolved` status via GraphQL |
| `submit_pending_review` | Submit pending reviews with specified event type |

### Issue Tools (3)
| Tool | Description |
| ---- | ----------- |
| `list_issues` | List all repository issues (filters out PRs automatically) |
| `review_issue` | Get issue details with comments, bot/user annotations |
| `reply_to_issue_comment` | Reply to issue comments |

### System Tools (1)
| Tool | Description |
| ---- | ----------- |
| `health` | Check server status and GitHub API rate limits |

## API Usage

**REST API** – PR/issue data, reviews, comments, replies
- `/repos/{owner}/{repo}/pulls/{number}` – PR data
- `/repos/{owner}/{repo}/issues/{number}` – Issue data (returns both issues and PRs)
- `/repos/{owner}/{repo}/issues?state={state}` – List issues (filtered to exclude PRs)

**GraphQL API** – `reviewThreads` (for `isResolved`), pending reviews

**Critical Notes**:
- Inline comment replies require `databaseId` (integer) not GraphQL `id` (string)
- `/issues` endpoint returns both issues and PRs – must filter by checking `pull_request` field
- `/pulls` endpoint only returns PRs (404 for issues)
