"""Queue interface for asynchronous message processing.

Provides abstraction for enqueuing jobs. Supports Azure Service Bus (production)
and in-memory queue (dev/test) for local development.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
import json
import time
import threading
import logging
from queue import Queue as ThreadQueue, Empty, Empty
from .models import JobPayload

logger = logging.getLogger(__name__)


class MessageQueue(ABC):
    """Abstract interface for message queue."""
    
    @abstractmethod
    def enqueue(self, payload: JobPayload) -> bool:
        """Enqueue a job for processing.
        
        Args:
            payload: Job payload to enqueue.
        
        Returns:
            True if enqueued successfully, False otherwise.
        """
        pass


class InMemoryQueue(MessageQueue):
    """In-memory queue for development and testing.
    
    Stores jobs in memory. Can be consumed by a worker thread.
    Thread-safe.
    """
    
    def __init__(self, maxsize: int = 1000):
        """Initialize in-memory queue.
        
        Args:
            maxsize: Maximum queue size (0 = unlimited).
        """
        self._queue: ThreadQueue = ThreadQueue(maxsize=maxsize)
        self._worker_callback: Optional[Callable[[JobPayload], None]] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
    
    def enqueue(self, payload: JobPayload) -> bool:
        """Enqueue job to in-memory queue."""
        try:
            queue_size_before = self._queue.qsize()
            self._queue.put_nowait(payload)
            queue_size_after = self._queue.qsize()
            logger.info("Job enqueued to in-memory queue", extra={
                "request_id": payload.request_id,
                "message_id": payload.message_id,
                "queue_size_before": queue_size_before,
                "queue_size_after": queue_size_after,
                "worker_running": self._running,
                "has_worker_callback": self._worker_callback is not None,
                "worker_thread_alive": self._worker_thread.is_alive() if self._worker_thread else False,
                "queue_id": id(self._queue),
                "thread_id": self._worker_thread.ident if self._worker_thread else None
            })
            return True
        except Exception as e:
            logger.error("Failed to enqueue job", extra={
                "request_id": payload.request_id,
                "message_id": payload.message_id,
                "error": str(e)
            })
            return False
    
    def set_worker(self, callback: Callable[[JobPayload], None]) -> None:
        """Set worker callback to process jobs.
        
        Args:
            callback: Function to call with each job payload.
        """
        self._worker_callback = callback
    
    def start_worker(self) -> None:
        """Start worker thread to process queued jobs."""
        if self._running:
            logger.warning("Worker already running")
            return
        
        if not self._worker_callback:
            logger.error("Cannot start worker: no callback set")
            return
        
        self._running = True
        logger.info("Starting worker thread", extra={
            "has_callback": self._worker_callback is not None,
            "queue_size": self._queue.qsize()
        })
        
        def worker():
            worker_logger = logging.getLogger(__name__)
            worker_logger.info("Worker thread started and running", extra={
                "queue_size": self._queue.qsize(),
                "has_callback": self._worker_callback is not None,
                "worker_running_flag": self._running
            })
            
            poll_count = 0
            last_log_time = time.time()
            while self._running:
                try:
                    # Log periodic status every 5 seconds to verify worker is alive
                    current_time = time.time()
                    if current_time - last_log_time >= 5.0:
                        worker_logger.info("Worker is alive and polling", extra={
                            "poll_count": poll_count,
                            "queue_size": self._queue.qsize(),
                            "worker_running": self._running,
                            "has_callback": self._worker_callback is not None,
                            "thread_id": threading.current_thread().ident
                        })
                        last_log_time = current_time
                    
                    # Log when we're about to get from queue (first few times)
                    if poll_count < 3:
                        worker_logger.info("Worker attempting to get from queue", extra={
                            "poll_count": poll_count,
                            "queue_size": self._queue.qsize(),
                            "queue_id": id(self._queue)
                        })
                    
                    payload = self._queue.get(timeout=1.0)
                    poll_count += 1
                    
                    if payload:
                        worker_logger.info("Worker picked up job from queue", extra={
                            "request_id": payload.request_id,
                            "message_id": payload.message_id,
                            "from_number": payload.from_number[:4] + "****" if payload.from_number else None,
                            "message_type": payload.message_type,
                            "queue_size_remaining": self._queue.qsize()
                        })
                        try:
                            if self._worker_callback:
                                worker_logger.debug("Calling worker callback", extra={
                                    "request_id": payload.request_id
                                })
                                self._worker_callback(payload)
                            else:
                                worker_logger.error("Worker callback is None!", extra={
                                    "request_id": payload.request_id
                                })
                        except Exception as e:
                            # Log error but continue processing
                            worker_logger.exception("Error processing job", extra={
                                "request_id": payload.request_id,
                                "message_id": payload.message_id,
                                "error": str(e)
                            })
                        finally:
                            self._queue.task_done()
                    else:
                        worker_logger.warning("Worker got None payload from queue", extra={
                            "queue_size": self._queue.qsize()
                        })
                except Empty:
                    # Timeout is expected - queue is empty, continue polling
                    poll_count += 1
                    continue
                except Exception as e:
                    # Other error
                    poll_count += 1
                    worker_logger.exception("Unexpected error in worker loop", extra={
                        "error": str(e),
                        "poll_count": poll_count
                    })
                    continue
            
            worker_logger.info("Worker thread exiting", extra={"final_poll_count": poll_count})
        
        self._worker_thread = threading.Thread(target=worker, daemon=True, name="MessageWorker")
        self._worker_thread.start()
        
        # Give thread a moment to start, then verify it's alive
        time.sleep(0.1)
        
        logger.info("Worker thread created and started", extra={
            "thread_name": self._worker_thread.name,
            "thread_alive": self._worker_thread.is_alive(),
            "thread_id": self._worker_thread.ident,
            "queue_id": id(self._queue),
            "worker_running_flag": self._running
        })
        
        if not self._worker_thread.is_alive():
            logger.error("Worker thread failed to start!")
    
    def stop_worker(self) -> None:
        """Stop worker thread."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)


class AzureServiceBusQueue(MessageQueue):
    """Azure Service Bus queue for production.
    
    Requires azure-servicebus package. Falls back to in-memory if unavailable.
    """
    
    def __init__(self, connection_string: Optional[str] = None, queue_name: str = "whatsapp-messages"):
        """Initialize Azure Service Bus queue.
        
        Args:
            connection_string: Azure Service Bus connection string.
            queue_name: Name of the queue.
        """
        self.connection_string = connection_string
        self.queue_name = queue_name
        self._client = None
        self._sender = None
        self._fallback = InMemoryQueue()
        self._init_servicebus()
    
    def _init_servicebus(self) -> None:
        """Initialize Azure Service Bus client."""
        try:
            from azure.servicebus import ServiceBusClient
            import os
            
            conn_str = self.connection_string or os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING")
            if not conn_str:
                return  # No connection string, use fallback
            
            self._client = ServiceBusClient.from_connection_string(conn_str)
            self._sender = self._client.get_queue_sender(queue_name=self.queue_name)
        except ImportError:
            # azure-servicebus package not installed
            pass
        except Exception:
            # Service Bus connection failed, use fallback
            self._client = None
            self._sender = None
    
    def enqueue(self, payload: JobPayload) -> bool:
        """Enqueue job to Azure Service Bus."""
        if self._sender:
            try:
                from azure.servicebus import ServiceBusMessage
                
                # Serialize payload
                payload_dict = {
                    "request_id": payload.request_id,
                    "message_id": payload.message_id,
                    "from_number": payload.from_number,
                    "message_type": payload.message_type,
                    "body": payload.body,
                    "num_media": payload.num_media,
                    "media_type": payload.media_type,
                    "product_id": payload.product_id,
                    "raw_message": payload.raw_message,
                    "timestamp": payload.timestamp
                }
                
                message = ServiceBusMessage(
                    body=json.dumps(payload_dict).encode('utf-8'),
                    message_id=payload.message_id,
                    application_properties={"request_id": payload.request_id}
                )
                
                self._sender.send_messages(message)
                return True
            except Exception:
                # Service Bus error, fallback to in-memory
                return self._fallback.enqueue(payload)
        else:
            return self._fallback.enqueue(payload)


def get_message_queue(connection_string: Optional[str] = None, queue_name: str = "whatsapp-messages") -> MessageQueue:
    """Factory function to get appropriate message queue.
    
    Args:
        connection_string: Optional Azure Service Bus connection string.
        queue_name: Queue name for Azure Service Bus.
    
    Returns:
        MessageQueue instance.
    """
    if connection_string:
        queue = AzureServiceBusQueue(connection_string, queue_name)
        if queue._client:
            return queue
    
    # Try environment variable
    import os
    conn_str_env = os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING")
    if conn_str_env:
        queue = AzureServiceBusQueue(conn_str_env, queue_name)
        if queue._client:
            return queue
    
    # Fallback to in-memory
    return InMemoryQueue()
