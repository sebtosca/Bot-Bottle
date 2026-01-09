"""Worker for processing enqueued message jobs.

This module handles the actual message processing that was enqueued
by the fast webhook handler. It contains the heavy processing logic
(LLM calls, database operations, external API calls).
"""

import logging
import time
from typing import Callable, Optional

from .models import JobPayload
from .queue import InMemoryQueue

logger = logging.getLogger(__name__)


class MessageWorker:
    """Worker for processing message jobs."""
    
    def __init__(self, processor: Callable[[JobPayload], None]):
        """Initialize message worker.
        
        Args:
            processor: Function to process job payloads.
        """
        self.processor = processor
        self._running = False
    
    def process_job(self, payload: JobPayload) -> None:
        """Process a single job payload.
        
        Args:
            payload: Job payload to process.
        """
        start_time = time.time()
        logger.info("Processing message job", extra={
            "request_id": payload.request_id,
            "message_id": payload.message_id
        })
        
        try:
            self.processor(payload)
            duration = time.time() - start_time
            logger.info("Message job processed successfully", extra={
                "request_id": payload.request_id,
                "message_id": payload.message_id,
                "duration_seconds": duration
            })
        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Error processing message job", extra={
                "request_id": payload.request_id,
                "message_id": payload.message_id,
                "duration_seconds": duration
            })
            raise


def setup_in_memory_worker(queue: InMemoryQueue, processor: Callable[[JobPayload], None]) -> None:
    """Set up in-memory queue worker for local development.
    
    Args:
        queue: InMemoryQueue instance.
        processor: Function to process job payloads.
    """
    worker = MessageWorker(processor)
    queue.set_worker(worker.process_job)
    queue.start_worker()
    logger.info("In-memory queue worker started", extra={
        "queue_type": type(queue).__name__,
        "has_processor": processor is not None
    })
