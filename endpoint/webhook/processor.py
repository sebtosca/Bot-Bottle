"""Message processor for handling enqueued WhatsApp messages.

This module contains the actual business logic that processes messages:
- Database operations
- LLM calls
- WhatsApp API calls
- Game logic
- etc.

This is called by the worker after a message is enqueued.
"""

import logging
from typing import Optional

from .models import JobPayload

logger = logging.getLogger(__name__)


def create_message_processor(
    process_message_func: callable
) -> callable:
    """Create a message processor function.
    
    Args:
        process_message_func: Function that takes (payload: JobPayload) and processes it.
                             This should contain all the heavy processing logic.
    
    Returns:
        Processor function compatible with MessageWorker.
    """
    def processor(payload: JobPayload) -> None:
        """Process a job payload.
        
        Args:
            payload: Job payload to process.
        """
        logger.info("Starting message processing", extra={
            "request_id": payload.request_id,
            "message_id": payload.message_id,
            "from_number": payload.from_number[:4] + "****",  # Partial for logging
            "message_type": payload.message_type
        })
        
        try:
            # Call the actual processing function
            process_message_func(payload)
        except Exception as e:
            logger.exception("Error in message processing", extra={
                "request_id": payload.request_id,
                "message_id": payload.message_id
            })
            raise
    
    return processor
