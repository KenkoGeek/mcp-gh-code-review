# Contributing to MCP GitHub Review Server

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/mcp-gh-code-review.git
   cd mcp-gh-code-review
   ```

2. **Set up development environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .[dev]
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub token
   ```

## Development Workflow

### Before Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Run tests to ensure everything works:
   ```bash
   pytest
   ```

### Making Changes

1. **Follow coding standards:**
   - Use type hints for all functions
   - Follow existing code patterns
   - Add docstrings for public functions
   - Keep functions focused and testable

2. **Run linting:**
   ```bash
   ruff check src/ tests/
   mypy src/
   ```

3. **Add tests for new functionality:**
   - Unit tests in `tests/`
   - Aim for >80% coverage
   - Test both success and error cases

4. **Test your changes:**
   ```bash
   pytest --cov=mcp_server
   ```

### Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Examples:
```
feat(server): add GraphQL client for pending reviews
fix(actions): validate PR metadata to prevent path traversal
docs: update README with GitHub token permissions
```

## Types of Contributions

### 🐛 Bug Reports

Use the bug report template and include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Relevant logs (sanitized)

### ✨ Feature Requests

Use the feature request template and include:
- Clear use case description
- Proposed solution
- Alternative approaches considered
- Implementation complexity estimate

### 🔧 Code Contributions

1. **Small fixes:** Direct PR with clear description
2. **New features:** Open an issue first to discuss approach
3. **Breaking changes:** Require discussion and approval

### 📚 Documentation

- README improvements
- Code comments and docstrings
- Architecture documentation
- Usage examples

## Code Review Process

1. **Automated checks must pass:**
   - All tests pass
   - Linting passes (ruff, mypy)
   - Coverage maintained

2. **Manual review criteria:**
   - Code follows project patterns
   - Tests cover new functionality
   - Documentation updated if needed
   - No security vulnerabilities

3. **Review timeline:**
   - Initial response: 2-3 business days
   - Full review: 1 week for complex changes
   - Follow-up responses: 1-2 business days

## Security

- **Never commit secrets** (tokens, keys, passwords)
- **Validate all inputs** using Pydantic models
- **Follow security best practices** in code
- **Report security issues** privately via GitHub Security tab

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=mcp_server --cov-report=term

# Specific test file
pytest tests/test_server_tools.py

# Dry-run mode testing
DRY_RUN=true pytest
```

### Writing Tests

- Use `pytest` fixtures for setup
- Mock external dependencies (GitHub API)
- Test error conditions
- Use `respx` for HTTP mocking

Example:
```python
@respx.mock
def test_apply_action():
    route = respx.post("https://api.github.com/repos/owner/repo/issues/1/labels")
    route.mock(return_value=Response(200, json={"labels": []}))
    
    # Test implementation
    assert route.called
```

## Architecture Guidelines

### MCP Protocol Compliance

- Implement proper JSON-RPC error codes
- Provide schemas for all tools
- Handle malformed requests gracefully
- Use structured logging

### Code Organization

- Keep modules focused (single responsibility)
- Use dependency injection
- Prefer composition over inheritance
- Use `__all__` to control public API

### Performance

- Reuse HTTP clients (connection pooling)
- Cache expensive operations
- Avoid N+1 queries
- Profile before optimizing

## Release Process

1. **Version bumping:** Use semantic versioning
2. **Changelog:** Update with notable changes
3. **Testing:** Full test suite on multiple Python versions
4. **Documentation:** Ensure docs are current
5. **Release notes:** Highlight breaking changes

## Getting Help

- **Questions:** Open a discussion or issue
- **Real-time chat:** Check if project has Discord/Slack
- **Documentation:** See `docs/` directory
- **Examples:** Check `tests/` for usage patterns

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments section

Thank you for contributing to make MCP GitHub Review Server better! 🚀