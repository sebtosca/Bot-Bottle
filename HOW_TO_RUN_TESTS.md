# How to Run Tests

## Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock freezegun
```

Or using the requirements file (if you have one):

```bash
pip install -r requirements-test.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=endpoint --cov-report=html
```

This generates:
- Terminal coverage report
- HTML report in `htmlcov/index.html`
- XML report for CI/CD

### Run Specific Test Categories

**Unit tests only:**
```bash
pytest -m unit
```

**Integration tests only:**
```bash
pytest -m integration
```

**End-to-end tests only:**
```bash
pytest -m e2e
```

### Run Tests for Specific Module

**Webhook tests:**
```bash
pytest endpoint/tests/unit/webhook/
```

**Security tests:**
```bash
pytest endpoint/tests/unit/security/
```

**All webhook tests (unit + integration):**
```bash
pytest endpoint/tests/unit/webhook/ endpoint/tests/integration/webhook/
```

### Run Specific Test File

```bash
pytest endpoint/tests/unit/webhook/test_parser.py
```

### Run Specific Test Function

```bash
pytest endpoint/tests/unit/webhook/test_parser.py::TestParseWebhookPayload::test_parse_production_webhook_format
```

## Test Output Options

### Verbose Output

```bash
pytest -v
```

### Very Verbose (shows each test)

```bash
pytest -vv
```

### Show Print Statements

```bash
pytest -s
```

### Stop on First Failure

```bash
pytest -x
```

### Stop after N Failures

```bash
pytest --maxfail=3
```

## Coverage Options

### Minimum Coverage Threshold

Tests will fail if coverage drops below threshold (set in `pytest.ini`):

```bash
pytest --cov-fail-under=80
```

### Coverage Report Formats

```bash
# Terminal + HTML
pytest --cov=endpoint --cov-report=term --cov-report=html

# Terminal + XML (for CI)
pytest --cov=endpoint --cov-report=term --cov-report=xml

# All formats
pytest --cov=endpoint --cov-report=term --cov-report=html --cov-report=xml
```

## Parallel Execution

For faster test runs (if pytest-xdist is installed):

```bash
pytest -n auto  # Auto-detect CPU count
pytest -n 4     # Use 4 workers
```

## Continuous Integration

Example CI configuration (GitHub Actions):

```yaml
- name: Run tests
  run: |
    pytest --cov=endpoint --cov-report=xml --cov-report=term
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Common Issues

### Import Errors

If you get import errors, ensure you're running from the project root:

```bash
cd /path/to/BotBottle
pytest
```

### Missing Dependencies

Install missing packages:

```bash
pip install pytest pytest-cov pytest-mock
```

### Database Connection Errors

Unit tests should not require a database. If you see DB errors:
- Check that mocks are properly set up
- Ensure `DATABASE_URL` is not set in test environment
- Use `clean_env` fixture for tests that need no env vars

### Time-Dependent Test Failures

If tests fail due to timing:
- Use `mock_time` fixture for deterministic time
- Increase timeouts in tests if needed
- Use `freezegun` for time mocking

## Test Organization

Tests are organized by:
- **Type**: unit, integration, e2e
- **Module**: webhook, security, middleware, routes, helpers
- **Location**: Tests are in `endpoint/tests/` or module-specific `tests/` directories

## Best Practices

1. **Run tests before committing:**
   ```bash
   pytest
   ```

2. **Check coverage before PR:**
   ```bash
   pytest --cov=endpoint --cov-report=term-missing
   ```

3. **Run fast tests during development:**
   ```bash
   pytest -m "not slow"
   ```

4. **Run all tests before release:**
   ```bash
   pytest -m "unit or integration or e2e"
   ```
