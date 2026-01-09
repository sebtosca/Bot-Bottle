# Webhook Ingestion System

Production-ready, scalable webhook ingestion system for WhatsApp/Meta Cloud API.

## Architecture

### Fast ACK Pattern
The webhook handler follows a fast ACK pattern:
1. **Verify signature** (if enabled)
2. **Parse payload** (pure function)
3. **Check idempotency** (prevent duplicates)
4. **Enqueue job** (async processing)
5. **Return 200 OK** (quickly)

All heavy processing (LLM calls, database operations, external API calls) happens in the worker, not in the request handler.

## Modules

### `models.py`
Data models using dataclasses:
- `WebhookEvent`: Structured representation of parsed webhook event
- `ParsedMessage`: Structured representation of parsed WhatsApp message
- `JobPayload`: Payload for enqueued processing jobs

### `parser.py`
Pure parsing functions (no Flask dependencies):
- `parse_webhook_payload()`: Parse and classify webhook events
- `parse_message()`: Parse message dict into ParsedMessage
- `extract_stable_id()`: Extract stable ID for idempotency

### `validator.py`
Security and validation:
- `verify_webhook_signature()`: Verify WhatsApp webhook signature (HMAC-SHA256)
- `verify_webhook_token()`: Verify webhook verification token (GET requests)

### `idempotency.py`
Idempotency store interface:
- `IdempotencyStore`: Abstract interface
- `InMemoryIdempotencyStore`: In-memory store for dev/test
- `RedisIdempotencyStore`: Redis store for production
- `get_idempotency_store()`: Factory function (auto-detects Redis)

### `queue.py`
Message queue interface:
- `MessageQueue`: Abstract interface
- `InMemoryQueue`: In-memory queue for dev/test
- `AzureServiceBusQueue`: Azure Service Bus for production
- `get_message_queue()`: Factory function (auto-detects Azure Service Bus)

### `handler.py`
Fast webhook handler:
- `WebhookHandler`: Main handler class
- `get_request_id()`: Extract or generate request ID
- Fast ACK pattern implementation

### `worker.py`
Message worker:
- `MessageWorker`: Worker for processing jobs
- `setup_in_memory_worker()`: Set up in-memory queue worker

### `processor.py`
Message processor:
- `create_message_processor()`: Create processor function
- `process_whatsapp_message()`: Placeholder for actual processing logic

## Usage

### Basic Setup

```python
from endpoint.webhook.handler import WebhookHandler
from endpoint.webhook.queue import get_message_queue, InMemoryQueue
from endpoint.webhook.worker import setup_in_memory_worker

# Initialize handler
webhook_handler = WebhookHandler(enable_signature_verification=True)
message_queue = get_message_queue()

# Set up worker (for in-memory queue in local dev)
if isinstance(message_queue, InMemoryQueue):
    processor = create_message_processor(process_whatsapp_message)
    setup_in_memory_worker(message_queue, processor)
```

### Flask Route

```python
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def whatsapp_webhook():
    request_id = get_request_id(request)
    
    if request.method == "GET":
        return webhook_handler.handle_verification(request)
    
    return webhook_handler.handle_webhook(request, request_id)
```

## Environment Variables

- `WHATSAPP_VERIFY_TOKEN`: Webhook verification token (for GET requests)
- `WHATSAPP_APP_SECRET`: App secret for signature verification (optional)
- `REDIS_URL`: Redis connection URL (optional, for idempotency)
- `AZURE_SERVICE_BUS_CONNECTION_STRING`: Azure Service Bus connection string (optional)

## Testing

Run unit tests:
```bash
pytest tests/test_webhook_*.py
```

## Migration Notes

The old synchronous processing logic in `endpoint.py` is still present but not called by the new handler. To complete the migration:

1. Extract processing logic from `endpoint.py`'s `whatsapp_webhook()` function
2. Move it to `message_processor.py`'s `process_whatsapp_message()` function
3. Remove the old handler code

The new handler is already integrated and will enqueue jobs. The worker will process them once `process_whatsapp_message()` is implemented.
