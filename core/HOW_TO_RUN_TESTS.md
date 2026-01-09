# How to Run Core Module Tests

## Quick Start

```bash
# Run all core tests
pytest core/tests/

# Run with coverage
pytest core/tests/ --cov=core --cov-report=html

# Run specific test type
pytest core/tests/unit/ -m unit
pytest core/tests/integration/ -m integration
pytest core/tests/e2e/ -m e2e
```

## Test Structure

```
core/tests/
├── unit/              # Fast, isolated unit tests
│   ├── game/          # Game logic tests
│   ├── points/        # Points system tests
│   └── state/         # State management tests
├── integration/       # Component integration tests
└── e2e/              # End-to-end flow tests
```

## Running Specific Tests

### By Module

```bash
# Game module tests
pytest core/tests/unit/game/

# Points module tests
pytest core/tests/unit/points/

# State module tests
pytest core/tests/unit/state/
```

### By Test File

```bash
# Emoji processing tests
pytest core/tests/unit/game/test_emoji_processing.py

# Points awarding tests
pytest core/tests/unit/points/test_points_awarding.py

# Message classification tests
pytest core/tests/unit/state/test_message_classification.py
```

### By Test Function

```bash
# Specific test function
pytest core/tests/unit/game/test_emoji_processing.py::TestGetEmojiCategory::test_get_emoji_category_found
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only E2E tests
pytest -m e2e

# Run tests that require database
pytest -m requires_db

# Run slow tests
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

## Coverage Reports

### Terminal Coverage

```bash
pytest core/tests/ --cov=core --cov-report=term-missing
```

### HTML Coverage Report

```bash
pytest core/tests/ --cov=core --cov-report=html
# Open htmlcov/index.html in browser
```

### XML Coverage Report (for CI)

```bash
pytest core/tests/ --cov=core --cov-report=xml
```

## Common Test Scenarios

### Run Tests with Verbose Output

```bash
pytest core/tests/ -v
```

### Run Tests and Stop on First Failure

```bash
pytest core/tests/ -x
```

### Run Tests with Detailed Failure Info

```bash
pytest core/tests/ -vv --tb=long
```

### Run Tests in Parallel (if pytest-xdist installed)

```bash
pytest core/tests/ -n auto
```

## Test Execution Examples

### Full Test Suite

```bash
# All tests with coverage
pytest core/tests/ \
    --cov=core \
    --cov-report=term-missing \
    --cov-report=html \
    -v
```

### Quick Unit Test Check

```bash
# Fast unit tests only
pytest core/tests/unit/ -m unit -v --tb=short
```

### Integration Test Check

```bash
# Integration tests (may require DB setup)
pytest core/tests/integration/ -m integration -v
```

## Troubleshooting

### Tests Failing Due to Missing Dependencies

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

### Tests Failing Due to Database

Integration and E2E tests may require database setup. Use test database:

```bash
# Set test database URL
export DATABASE_URL="postgresql://user:pass@localhost/test_db"
pytest core/tests/integration/ -m requires_db
```

### Tests Failing Due to Missing Files

Some tests mock file system operations. If you see file-related errors:

- Check that `emoji_segmentation_corrected.json` exists (or is mocked)
- Verify test fixtures are set up correctly
- Check `conftest.py` for file mocking setup

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run core tests
  run: |
    pytest core/tests/ \
      --cov=core \
      --cov-report=xml \
      --cov-fail-under=80 \
      -v
```

### Coverage Threshold

Tests are configured to fail if coverage drops below 80%:

```bash
pytest core/tests/ --cov=core --cov-fail-under=80
```

## Best Practices

1. **Run tests before committing**: `pytest core/tests/unit/ -m unit`
2. **Check coverage regularly**: `pytest core/tests/ --cov=core --cov-report=term`
3. **Fix failing tests immediately**: Don't let them accumulate
4. **Write tests for new features**: Maintain coverage above 80%
5. **Use appropriate markers**: Mark tests as `unit`, `integration`, or `e2e`

## Test Development

When adding new tests:

1. Place in appropriate directory (`unit/`, `integration/`, or `e2e/`)
2. Use descriptive test names: `test_function_name_scenario`
3. Follow Arrange-Act-Assert pattern
4. Mock external dependencies in unit tests
5. Use fixtures from `conftest.py` for common setup
6. Mark tests appropriately (`@pytest.mark.unit`, etc.)
