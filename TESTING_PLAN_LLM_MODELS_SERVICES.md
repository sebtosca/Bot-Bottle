# Testing Plan: LLM, Models, and Services

## Overview

This document outlines the testing strategy for:
- `llm/` - LLM integration (Mistral AI)
- `models/` - Character models and configuration
- `services/` - External service clients (WhatsApp Cloud API)

## Test Pyramid

### Unit Tests (70%)
**Fast, isolated, heavily mocked, no I/O**

**llm/llama_client.py:**
- Mock Mistral API client
- Test prompt building logic
- Test response parsing
- Test error handling
- Test fallback behaviors
- Test JSON extraction from LLM responses
- Test emotion validation

**models/characters.py:**
- Test character config retrieval
- Test fallback to default character
- Test system prompt extraction
- Test character ID extraction
- Test edge cases (invalid product_id, missing fields)

**services/whatsapp/client.py:**
- Mock `requests.post`
- Test payload construction
- Test error response parsing
- Test header generation
- Test URL construction
- Test error handling (network, API errors, invalid JSON)
- Test message ID extraction
- Test phone number normalization logging

### Integration Tests (25%)
**Real components wired together**

**llm/llama_client.py:**
- Test with real Mistral client (if API key available, otherwise skip)
- Test end-to-end API call flow
- Test error recovery

**services/whatsapp/client.py:**
- Test with mocked HTTP responses
- Test full request/response cycle
- Test error propagation

### End-to-End Tests (5%)
**Minimal, critical paths only**

- Test complete LLM → Character → WhatsApp flow (if possible)
- Test error handling across service boundaries

## Folder Structure

```
llm/
├── llama_client.py
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures
    ├── unit/
    │   ├── __init__.py
    │   └── test_llama_client.py
    ├── integration/
    │   ├── __init__.py
    │   └── test_llama_integration.py
    └── e2e/
        ├── __init__.py
        └── test_llama_e2e.py

models/
├── characters.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── __init__.py
    │   └── test_characters.py
    └── integration/
        ├── __init__.py
        └── test_characters_integration.py

services/
└── whatsapp/
    ├── client.py
    └── tests/
        ├── __init__.py
        ├── conftest.py
        ├── unit/
        │   ├── __init__.py
        │   └── test_client.py
        ├── integration/
        │   ├── __init__.py
        │   └── test_client_integration.py
        └── e2e/
            ├── __init__.py
            └── test_client_e2e.py
```

## Mocking Strategy

### LLM Module
- **Unit tests**: Mock `mistralai.Mistral` class and `client.chat.complete()` method
- **Integration tests**: Use real Mistral client if API key available (skip otherwise)
- **E2E tests**: Use real API with test credentials

### Models Module
- **Unit tests**: No mocking needed (pure functions)
- **Integration tests**: Test with real CHARACTERS dict

### Services Module
- **Unit tests**: Mock `requests.post` using `unittest.mock.patch`
- **Integration tests**: Use `responses` library or mock HTTP responses
- **E2E tests**: Use test WhatsApp API credentials (if available)

## Fixtures Strategy

### Shared Fixtures (conftest.py)
- Mock Mistral client
- Mock requests responses
- Sample conversation histories
- Sample bottle states
- Sample WhatsApp API responses
- Environment variable mocks

## Edge Cases to Test

### LLM Module
- Missing API key
- Invalid API key
- Network errors
- API rate limits
- Empty responses
- Invalid JSON in sentiment analysis
- Invalid emotion values
- Response truncation
- None content responses
- Tool calls instead of content

### Models Module
- Invalid product_id
- Missing character config
- Empty product_id
- Non-string product_id
- Missing fields in config

### Services Module
- Missing access token
- Missing phone number ID
- Network timeouts
- Invalid JSON responses
- HTTP 200 with error in body
- Missing message ID in response
- Empty messages array
- Phone number normalization
- Rate limiting errors
- Permission errors (code 10)
- Invalid phone numbers
- Empty message body
- Very long message body
- Invalid media URLs
- Too many buttons/options

## Coverage Goals

- **Unit tests**: 90%+ coverage
- **Integration tests**: 70%+ coverage
- **E2E tests**: Critical paths only

## Test Execution

- Unit tests: < 1 second each
- Integration tests: < 5 seconds each
- E2E tests: < 30 seconds each (if API available)

## CI/CD Integration

- Run unit tests on every commit
- Run integration tests on PR
- Run E2E tests on merge to main (if API keys available)
