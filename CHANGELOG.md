# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial MCP GitHub Review Server implementation
- 7 JSON-RPC tools for comprehensive PR review automation
- Bot detection with configurable patterns
- Webhook integration with GitHub signature verification
- SQLite-backed thread mappings for retry safety
- YAML-driven policy engine for triage rules
- Production-ready logging, error handling, and rate limiting
- Docker support for containerized deployment
- Comprehensive test suite with 37% coverage
- Community files: Code of Conduct, Contributing guidelines, Issue templates
- CI/CD pipeline with linting, testing, and security scanning

### Features
- **review_pr**: Primary entry point for comprehensive PR analysis
- **apply_actions**: Execute GitHub API actions with dry-run support
- **generate_reply**: Context-aware responses for comment threads
- **get_pending_reviews**: GraphQL-based pending review management
- **submit_pending_review**: Submit pending reviews with event types
- **set_policy**: Runtime policy updates
- **health**: Server status and rate limit monitoring

### Technical
- Modern Python 3.11+ with type hints and match/case patterns
- MCP protocol compliance with JSON-RPC over stdio
- GitHub REST and GraphQL API integration
- Structured logging with contextual information
- Security-first design with input validation and token protection