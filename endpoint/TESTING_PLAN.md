# Testing Strategy for Endpoint Module

## Test Pyramid Structure

### 1. Unit Tests (70% of tests)
**Location**: `endpoint/*/tests/unit/`

**Characteristics**:
- Fast execution (< 1ms per test)
- No I/O operations
- Heavy mocking of external dependencies
- Test individual functions/classes in isolation

**What to Test**:
- **webhook/parser.py**: Message parsing logic, edge cases
- **webhook/models.py**: Data model validation
- **webhook/validator.py**: Signature verification logic
- **webhook/idempotency.py**: Duplicate detection logic
- **webhook/queue.py**: Queue operations (mocked)
- **security/validation.py**: Input sanitization, validation rules
- **security/rate_limiter.py**: Rate limiting algorithm
- **middleware/request_correlation.py**: Request ID generation
- **helpers/slang.py**: Text transformation logic

### 2. Integration Tests (25% of tests)
**Location**: `endpoint/*/tests/integration/`

**Characteristics**:
- Real components wired together
- Test database (isolated, cleaned between tests)
- Real queue operations (in-memory)
- Mock external APIs (WhatsApp, LLM)

**What to Test**:
- **webhook/handler.py**: Full webhook flow (verify → parse → enqueue)
- **webhook/queue.py + worker.py**: Queue → Worker → Processor flow
- **routes/static_files.py**: File serving with real filesystem
- **security/middleware.py**: Rate limiting with real limiter
- **endpoint.py**: Flask app initialization and route registration

### 3. End-to-End Tests (5% of tests)
**Location**: `endpoint/tests/e2e/`

**Characteristics**:
- Minimal tests (3-5 critical paths)
- Real Flask test client
- Test database
- Mock external services
- Validate complete user flows

**What to Test**:
- Complete webhook flow: POST → verification → parsing → enqueue → process → response
- Health check endpoint
- Static file serving end-to-end
- Error handling and recovery

## Folder Structure

```
endpoint/
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── unit/                    # Unit tests
│   │   ├── webhook/
│   │   │   ├── test_parser.py
│   │   │   ├── test_models.py
│   │   │   ├── test_validator.py
│   │   │   ├── test_idempotency.py
│   │   │   └── test_queue.py
│   │   ├── security/
│   │   │   ├── test_validation.py
│   │   │   └── test_rate_limiter.py
│   │   ├── middleware/
│   │   │   └── test_request_correlation.py
│   │   └── helpers/
│   │       └── test_slang.py
│   ├── integration/             # Integration tests
│   │   ├── webhook/
│   │   │   ├── test_handler.py
│   │   │   └── test_worker_integration.py
│   │   ├── routes/
│   │   │   └── test_static_files.py
│   │   └── security/
│   │       └── test_middleware_integration.py
│   └── e2e/                     # End-to-end tests
│       ├── test_webhook_flow.py
│       └── test_static_serving.py
├── webhook/
│   └── tests/                   # Module-specific tests (if needed)
├── security/
│   └── tests/
├── middleware/
│   └── tests/
├── routes/
│   └── tests/
└── helpers/
    └── tests/
```

## Mocking Strategy

### External Dependencies to Mock:
1. **Database**: Use SQLite in-memory for tests
2. **WhatsApp API**: Mock `requests.post` calls
3. **LLM Service**: Mock LLM client calls
4. **File System**: Use `tempfile` or `pathlib.Path` mocking
5. **Redis**: Mock or use in-memory fallback
6. **Time**: Use `freezegun` or `unittest.mock.patch` for time-dependent tests
7. **Random**: Seed random number generator for deterministic tests

### Fixtures:
- `app`: Flask test client
- `db_session`: Test database session
- `mock_whatsapp_api`: Mocked WhatsApp API responses
- `mock_llm`: Mocked LLM responses
- `sample_webhook_payload`: Sample webhook JSON
- `sample_message`: Sample parsed message
- `rate_limiter`: In-memory rate limiter
- `idempotency_store`: In-memory idempotency store
- `message_queue`: In-memory message queue

## Edge Cases to Test

### Webhook Handler:
- Invalid JSON payload
- Missing required fields
- Invalid signature
- Duplicate messages
- Status updates (not messages)
- Unknown event types
- Queue full scenarios
- Network errors

### Message Parser:
- Malformed webhook structure
- Missing message fields
- Different webhook formats (production vs test)
- Interactive messages (buttons/lists)
- Media messages
- Empty messages

### Validation:
- Path traversal attempts
- SQL injection attempts
- XSS attempts
- Invalid file extensions
- Oversized filenames
- Special characters in filenames

### Rate Limiting:
- Burst requests
- Slow requests over time
- Multiple IPs
- Edge of time window
- Concurrent requests

### Queue:
- Queue full
- Worker not started
- Worker callback errors
- Concurrent enqueue
- Empty queue polling

## Coverage Goals

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: 80%+ coverage
- **Overall**: 85%+ coverage

## CI/CD Integration

- Run tests on every commit
- Fail build if coverage drops below threshold
- Generate coverage reports
- Run tests in parallel where possible
