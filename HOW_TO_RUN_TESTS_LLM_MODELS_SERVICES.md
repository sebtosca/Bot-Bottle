# How to Run Tests for LLM, Models, and Services

## Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

## Running Tests

### Run All Tests

```bash
# Run all tests (endpoint + llm + models + services)
pytest

# Run with coverage
pytest --cov=llm --cov=models --cov=services --cov-report=html

# Run with verbose output
pytest -v
```

### Run Tests by Module

**LLM Module:**
```bash
# All LLM tests
pytest llm/tests/

# Unit tests only
pytest llm/tests/unit/ -m unit

# Integration tests only
pytest llm/tests/integration/ -m integration

# E2E tests only (requires MISTRAL_API_KEY)
pytest llm/tests/e2e/ -m e2e
```

**Models Module:**
```bash
# All models tests
pytest models/tests/

# Unit tests only
pytest models/tests/unit/ -m unit

# Integration tests only
pytest models/tests/integration/ -m integration
```

**Services Module:**
```bash
# All WhatsApp service tests
pytest services/whatsapp/tests/

# Unit tests only
pytest services/whatsapp/tests/unit/ -m unit

# Integration tests only
pytest services/whatsapp/tests/integration/ -m integration

# E2E tests only (requires WhatsApp credentials)
pytest services/whatsapp/tests/e2e/ -m e2e
```

### Run Tests by Category

```bash
# Run all unit tests
pytest -m unit

# Run all integration tests
pytest -m integration

# Run all E2E tests (may require API keys)
pytest -m e2e
```

### Run Specific Test Files

```bash
# LLM unit tests
pytest llm/tests/unit/test_llama_client.py

# Models unit tests
pytest models/tests/unit/test_characters.py

# WhatsApp client unit tests
pytest services/whatsapp/tests/unit/test_client.py
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest llm/tests/unit/test_llama_client.py::TestGenerateReplyMistral

# Run specific test function
pytest models/tests/unit/test_characters.py::TestGetCharacterConfig::test_get_cherry_config
```

## Coverage Reporting

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=llm --cov=models --cov=services --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=llm --cov=models --cov=services --cov-report=html
# Then open: htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=llm --cov=models --cov=services --cov-report=xml
```

### Coverage by Module

```bash
# LLM coverage
pytest --cov=llm --cov-report=term-missing llm/tests/

# Models coverage
pytest --cov=models --cov-report=term-missing models/tests/

# Services coverage
pytest --cov=services --cov-report=term-missing services/whatsapp/tests/
```

## Test Execution Options

### Stop on First Failure

```bash
pytest -x
```

### Show Local Variables on Failure

```bash
pytest -l
```

### Run Tests in Parallel (faster)

```bash
pytest -n auto  # Requires pytest-xdist
```

### Show Print Statements

```bash
pytest -s
```

### Verbose Output with Test Names

```bash
pytest -v
```

## Environment Variables for E2E Tests

E2E tests require API credentials. Set these in your environment:

```bash
# For LLM E2E tests
export MISTRAL_API_KEY="your_api_key"
export MISTRAL_MODEL_NAME="mistral-small"  # Optional, has default

# For WhatsApp E2E tests
export WHATSAPP_ACCESS_TOKEN="your_token"
export WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
export TEST_WHATSAPP_PHONE="+33684950535"  # Test phone number
```

**Note:** E2E tests are automatically skipped if credentials are not set.

## Common Issues

### Import Errors

If you get import errors, make sure you're running from the project root:
```bash
cd /path/to/BotBottle
pytest
```

### Missing Dependencies

Install all test dependencies:
```bash
pip install pytest pytest-cov pytest-mock freezegun
```

### Tests Hanging

Some tests use worker threads. If tests hang:
- Check for background threads not stopping
- Use `pytest --timeout=30` to add timeout (requires pytest-timeout)

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run tests
  run: |
    pytest --cov=llm --cov=models --cov=services --cov-report=xml --cov-report=term
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

### Coverage Threshold

The pytest.ini file sets a minimum coverage threshold of 80%. To check:
```bash
pytest --cov=llm --cov=models --cov=services --cov-fail-under=80
```

## Test Statistics

After running tests, you'll see output like:
```
========================= 150 passed in 12.34s =========================
```

For detailed statistics:
```bash
pytest --co -q  # Show collected tests
pytest -v       # Show each test result
```
