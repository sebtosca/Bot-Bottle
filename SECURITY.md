# Security Implementation

This document describes the security measures implemented in the BotBottle application.

## Security Features

### 1. Rate Limiting

**Implementation**: `endpoint/security/rate_limiter.py`

- **IP-based rate limiting**: All public endpoints are rate limited per IP address
- **User-based rate limiting**: Supports per-user rate limiting (when authentication is added)
- **Backends**:
  - Redis (production) - sliding window with sorted sets
  - In-memory (dev/test) - thread-safe in-memory store
- **Default limits**:
  - Webhook: 100 requests/minute
  - Static files: 200 requests/minute
  - Health check: 60 requests/minute
  - Stats image: 30 requests/minute (expensive operation)

**Response**: Returns HTTP 429 with `Retry-After` header when limit exceeded.

### 2. Input Validation and Sanitization

**Implementation**: `endpoint/security/validation.py`

- **Schema-based validation**: Structured validation using `SchemaValidator`
- **Type checking**: Validates data types match expected schema
- **Length limits**: Enforces min/max length on strings
- **Pattern validation**: Regex-based format validation
- **Sanitization functions**:
  - `sanitize_string()`: Removes control characters, trims whitespace
  - `sanitize_filename()`: Prevents path traversal, validates filenames
- **Strict mode**: Rejects unexpected fields in validated data

**Applied to**:
- All filename parameters in static file routes
- Product IDs in query parameters
- Message IDs and phone numbers

### 3. API Key Security

**Implementation**: `endpoint/security/api_keys.py`

- **No hardcoded keys**: All keys read from environment variables
- **Secure retrieval**: `SecureAPIKey` class prevents key exposure
- **Logging safety**: Keys are never logged (only masked previews)
- **Validation**: `validate_api_keys()` checks all required keys on startup
- **Key rotation**: Supports key rotation via environment variable updates

**Protected keys**:
- `WHATSAPP_ACCESS_TOKEN` (required)
- `WHATSAPP_PHONE_NUMBER_ID` (required)
- `WHATSAPP_VERIFY_TOKEN` (required)
- `MISTRAL_API_KEY` (required)
- `WHATSAPP_APP_SECRET` (optional, for signature verification)

### 4. Security Headers

**Implementation**: `endpoint/security/middleware.py`

OWASP-compliant security headers:
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Content-Security-Policy` - Restrictive CSP for API endpoints
- `Strict-Transport-Security` - HSTS (HTTPS only)

### 5. Request Correlation

**Implementation**: `endpoint/middleware/request_correlation.py`

- **Request ID**: Every request gets a unique ID (from `X-Request-ID` header or generated)
- **Log correlation**: All log entries include `request_id` for tracing
- **Flask g integration**: Request ID stored in Flask `g` for access throughout request lifecycle

### 6. Webhook Security

**Implementation**: `endpoint/webhook/validator.py`

- **Signature verification**: HMAC-SHA256 signature verification (optional, enabled by default)
- **Token verification**: Webhook verification token for GET requests
- **Fast failure**: Returns 403 immediately on verification failure

### 7. Structured Logging

**Implementation**: Throughout codebase

- **No PII in logs**: Phone numbers, message content, API keys are never logged
- **Log levels**: Appropriate levels (DEBUG, INFO, WARNING, ERROR)
- **Request correlation**: All logs include `request_id`
- **Structured data**: Uses `extra=` parameter for structured logging

## OWASP Best Practices

### A01:2021 – Broken Access Control
- ✅ Rate limiting prevents abuse
- ✅ Input validation prevents injection attacks
- ✅ Filename sanitization prevents path traversal

### A02:2021 – Cryptographic Failures
- ✅ API keys stored in environment variables (never in code)
- ✅ Keys never logged or exposed
- ✅ HTTPS enforced via HSTS header

### A03:2021 – Injection
- ✅ Input validation and sanitization
- ✅ Filename validation prevents path traversal
- ✅ Type checking prevents type confusion attacks

### A04:2021 – Insecure Design
- ✅ Fast ACK pattern prevents timeout attacks
- ✅ Idempotency prevents duplicate processing
- ✅ Queue-based processing isolates failures

### A05:2021 – Security Misconfiguration
- ✅ Security headers configured
- ✅ Error messages don't expose sensitive information
- ✅ Default secure configurations

### A07:2021 – Identification and Authentication Failures
- ✅ Webhook signature verification
- ✅ Token-based verification for webhook setup
- ✅ Rate limiting prevents brute force

### A08:2021 – Software and Data Integrity Failures
- ✅ Signature verification for webhooks
- ✅ Input validation prevents tampering

## Environment Variables

All sensitive configuration is stored in environment variables:

```bash
# Required
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
MISTRAL_API_KEY=...

# Optional
WHATSAPP_APP_SECRET=...  # For signature verification
REDIS_URL=...  # For production rate limiting
AZURE_SERVICE_BUS_CONNECTION_STRING=...  # For production queue
```

## Deployment Checklist

- [ ] All environment variables set
- [ ] Redis configured (for production rate limiting)
- [ ] Azure Service Bus configured (for production queue)
- [ ] HTTPS enabled (for HSTS)
- [ ] Security headers verified
- [ ] Rate limits tuned for expected load
- [ ] Logging configured (structured logs)
- [ ] Monitoring set up (for rate limit violations)

## Testing

Run security tests:
```bash
# Test rate limiting
python -m pytest tests/test_security_rate_limiter.py

# Test input validation
python -m pytest tests/test_security_validation.py

# Test API key handling
python -m pytest tests/test_security_api_keys.py
```
