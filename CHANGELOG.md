# [1.1.0](https://github.com/KenkoGeek/mcp-gh-code-review/compare/v1.0.0...v1.1.0) (2025-10-05)


### Features

* **issues:** add review_issue and reply_to_issue_comment tools ([#9](https://github.com/KenkoGeek/mcp-gh-code-review/issues/9)) ([2fb66a7](https://github.com/KenkoGeek/mcp-gh-code-review/commit/2fb66a7b150f5e1f26a3c9406ce2154614f114a8))

# 1.0.0 (2025-10-05)


### Bug Fixes

* **ci:** add permissions to codeql job call ([e92e369](https://github.com/KenkoGeek/mcp-gh-code-review/commit/e92e369aac0e35584db57c76905efa5ccd3952f4))
* **ci:** add permissions to codeql job call ([e9f623e](https://github.com/KenkoGeek/mcp-gh-code-review/commit/e9f623ebd382ab8e90e067f5cb25ffd4dad171a6))
* **ci:** add permissions to codeql job call ([d3a1b40](https://github.com/KenkoGeek/mcp-gh-code-review/commit/d3a1b40e98c9966546f84946dc31ba57e5e166e5))
* **ci:** add permissions to codeql job call ([f25fa3a](https://github.com/KenkoGeek/mcp-gh-code-review/commit/f25fa3a0938d111a8618a7b47e2e3122780ddff9))
* **ci:** add permissions to codeql job call ([40939a2](https://github.com/KenkoGeek/mcp-gh-code-review/commit/40939a28dce5b8d8373d9ac1586f0328a2403eb7))
* **ci:** add security-events permission to ci job call ([3c24c4b](https://github.com/KenkoGeek/mcp-gh-code-review/commit/3c24c4b7321e75005714e31abef94dfd784f8861))
* **ci:** remove npm cache from setup-node ([9863cb9](https://github.com/KenkoGeek/mcp-gh-code-review/commit/9863cb93c805ab79eaf2c3eb3f02c59136e8ff86))
* **ci:** resolve concurrency deadlock between release and ci workflows ([55726a3](https://github.com/KenkoGeek/mcp-gh-code-review/commit/55726a366261f8a4629ccf352d9bb1c70d6c4eed))
* **ci:** use RELEASE_TOKEN to bypass branch protection ([eb48e2a](https://github.com/KenkoGeek/mcp-gh-code-review/commit/eb48e2a828824cc765a583974cbf57adea85c57c))


### Features

* **server:** Build mcp server for GitHub reviews ([0526b65](https://github.com/KenkoGeek/mcp-gh-code-review/commit/0526b655646d5c77ccd3ffc836991a5e3238d657))

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
