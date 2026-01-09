"""Unit tests for message queue."""

import pytest
import threading
import time
from endpoint.webhook.queue import InMemoryQueue, MessageQueue
from endpoint.webhook.models import JobPayload


class TestInMemoryQueue:
    """Tests for InMemoryQueue."""
    
    def test_enqueue_success(self, sample_job_payload):
        """Test successfully enqueuing a job."""
        queue = InMemoryQueue()
        
        result = queue.enqueue(sample_job_payload)
        
        assert result is True
        assert queue._queue.qsize() == 1
    
    def test_enqueue_multiple(self, sample_job_payload):
        """Test enqueuing multiple jobs."""
        queue = InMemoryQueue()
        
        payload1 = sample_job_payload
        payload2 = JobPayload(
            request_id="test-request-456",
            message_id="wamid.test456",
            from_number="15551234567",
            message_type="text",
            body="Second message",
            num_media=0,
            media_type="",
            product_id="00001",
            raw_message={},
            timestamp=time.time()
        )
        
        queue.enqueue(payload1)
        queue.enqueue(payload2)
        
        assert queue._queue.qsize() == 2
    
    def test_enqueue_queue_full(self, sample_job_payload):
        """Test enqueuing when queue is full."""
        queue = InMemoryQueue(maxsize=1)
        
        # Fill queue
        queue.enqueue(sample_job_payload)
        
        # Try to enqueue another (should fail)
        payload2 = JobPayload(
            request_id="test-request-456",
            message_id="wamid.test456",
            from_number="15551234567",
            message_type="text",
            body="Second message",
            num_media=0,
            media_type="",
            product_id="00001",
            raw_message={},
            timestamp=time.time()
        )
        
        # This will raise Queue.Full, but we catch it
        with pytest.raises(Exception):  # Queue.Full or similar
            queue._queue.put_nowait(payload2)
    
    def test_set_worker(self):
        """Test setting worker callback."""
        queue = InMemoryQueue()
        
        def dummy_worker(payload):
            pass
        
        queue.set_worker(dummy_worker)
        
        assert queue._worker_callback is not None
    
    def test_start_worker_without_callback(self):
        """Test starting worker without callback."""
        queue = InMemoryQueue()
        
        # Should not start without callback
        queue.start_worker()
        
        # Worker should not be running
        assert queue._running is False
    
    def test_start_worker_with_callback(self):
        """Test starting worker with callback."""
        queue = InMemoryQueue()
        
        processed = []
        
        def worker(payload):
            processed.append(payload)
        
        queue.set_worker(worker)
        queue.start_worker()
        
        # Give thread time to start
        time.sleep(0.1)
        
        assert queue._running is True
        assert queue._worker_thread is not None
        assert queue._worker_thread.is_alive()
        
        # Cleanup
        queue.stop_worker()
    
    def test_worker_processes_jobs(self, sample_job_payload):
        """Test worker processes enqueued jobs."""
        queue = InMemoryQueue()
        processed = []
        
        def worker(payload):
            processed.append(payload)
        
        queue.set_worker(worker)
        queue.start_worker()
        
        # Give thread time to start
        time.sleep(0.1)
        
        # Enqueue job
        queue.enqueue(sample_job_payload)
        
        # Wait for processing
        time.sleep(0.2)
        
        assert len(processed) == 1
        assert processed[0].message_id == sample_job_payload.message_id
        
        # Cleanup
        queue.stop_worker()
    
    def test_stop_worker(self):
        """Test stopping worker."""
        queue = InMemoryQueue()
        
        def worker(payload):
            pass
        
        queue.set_worker(worker)
        queue.start_worker()
        
        time.sleep(0.1)
        assert queue._running is True
        
        queue.stop_worker()
        
        time.sleep(0.1)
        assert queue._running is False
    
    def test_worker_handles_errors(self, sample_job_payload):
        """Test worker handles processing errors gracefully."""
        queue = InMemoryQueue()
        errors = []
        
        def failing_worker(payload):
            raise ValueError("Processing error")
        
        queue.set_worker(failing_worker)
        queue.start_worker()
        
        time.sleep(0.1)
        
        # Enqueue job - should not crash worker
        queue.enqueue(sample_job_payload)
        
        # Wait a bit
        time.sleep(0.2)
        
        # Worker should still be running
        assert queue._running is True
        
        # Cleanup
        queue.stop_worker()
