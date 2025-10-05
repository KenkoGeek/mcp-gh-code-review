---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: ['bug', 'triage']
assignees: ''
---

## Bug Description

A clear and concise description of what the bug is.

## Steps to Reproduce

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

A clear and concise description of what actually happened.

## Environment

- **OS:** [e.g. macOS 14.0, Ubuntu 22.04, Windows 11]
- **Python version:** [e.g. 3.11.5]
- **MCP Server version:** [e.g. 0.1.0]
- **GitHub token type:** [Fine-grained/Classic]
- **Deployment method:** [Local/Docker/Cloud]

## Configuration

```yaml
# Sanitized policy.yaml (remove sensitive data)
labels:
  src/: [core]
# ... rest of config
```

## Logs

```
# Relevant log output (sanitize any tokens/secrets)
2024-01-01 12:00:00 [ERROR] action_failed: GitHub API error
```

## Additional Context

- Is this reproducible consistently?
- Does it happen in dry-run mode?
- Any recent changes to configuration?
- Screenshots if applicable

## Possible Solution

If you have ideas on how to fix this, please share them here.