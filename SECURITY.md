# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**DO NOT** open public issues for security vulnerabilities.

### How to Report

Email security concerns to: **info@kenkogeek.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: 7 days, High: 14 days, Medium: 30 days)

## Security Best Practices

### Deployment

- Never commit secrets to repository
- Use environment variables or secret managers for credentials
- Enable webhook signature verification (`WEBHOOK_SECRET`)
- Run containers as non-root user (default in Dockerfile)
- Use GitHub Apps with minimal permissions over personal tokens
- Enable rate limit monitoring via health endpoint

### GitHub Token Permissions

Minimum required scopes:
- `repo` - For private repositories
- `public_repo` - For public repositories only
- `read:org` - If using organization-level policies

### Webhook Security

- Always set `WEBHOOK_SECRET` in production
- Verify `X-Hub-Signature-256` header on all webhook requests
- Use HTTPS endpoints only
- Implement rate limiting on webhook endpoint

### Database Security

- Store SQLite database outside web-accessible directories
- Set appropriate file permissions (600)
- Regular backups of thread mappings
- Use `DB_PATH` to control location

### Logging

- Structured logs never include tokens or secrets
- Sanitize user input in log messages
- Use `LOG_LEVEL=INFO` in production (avoid DEBUG)

## Known Security Considerations

- **Dry-run mode**: Test mode bypasses GitHub API writes but still validates tokens
- **Thread storage**: SQLite database contains PR metadata (no sensitive data)
- **Rate limits**: Monitor via health endpoint to prevent service disruption
