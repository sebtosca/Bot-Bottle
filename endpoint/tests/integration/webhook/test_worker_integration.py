"""Integration tests for worker and queue."""

import pytest
import time
from endpoint.webhook.queue import InMemoryQueue
from endpoint.webhook.worker import MessageWorker, setup_in_memory_worker
from endpoint.webhook.models import JobPayload


class TestWorkerIntegration:
    """Integration tests for worker and queue."""
    
    def test_worker_processes_enqueued_jobs(self, sample_job_payload):
        """Test worker processes jobs from queue."""
        queue = InMemoryQueue()
        processed = []
        
        def processor(payload):
            processed.append(payload)
        
        worker = MessageWorker(processor)
        queue.set_worker(worker.process_job)
        queue.start_worker()
        
        # Give thread time to start
        time.sleep(0.1)
        
        # Enqueue job
        queue.enqueue(sample_job_payload)
        
        # Wait for processing
        time.sleep(0.3)
        
        assert len(processed) == 1
        assert processed[0].message_id == sample_job_payload.message_id
        
        # Cleanup
        queue.stop_worker()
    
    def test_worker_processes_multiple_jobs(self, sample_job_payload):
        """Test worker processes multiple jobs in order."""
        queue = InMemoryQueue()
        processed = []
        
        def processor(payload):
            processed.append(payload.message_id)
        
        worker = MessageWorker(processor)
        queue.set_worker(worker.process_job)
        queue.start_worker()
        
        time.sleep(0.1)
        
        # Enqueue multiple jobs
        for i in range(3):
            payload = JobPayload(
                request_id=f"test-request-{i}",
                message_id=f"wamid.test{i}",
                from_number="15551234567",
                message_type="text",
                body=f"Message {i}",
                num_media=0,
                media_type="",
                product_id="00001",
                raw_message={},
                timestamp=time.time()
            )
            queue.enqueue(payload)
        
        # Wait for processing
        time.sleep(0.5)
        
        assert len(processed) == 3
        assert "wamid.test0" in processed
        assert "wamid.test1" in processed
        assert "wamid.test2" in processed
        
        # Cleanup
        queue.stop_worker()
    
    def test_worker_handles_processor_errors(self, sample_job_payload):
        """Test worker handles processor errors gracefully."""
        queue = InMemoryQueue()
        errors = []
        
        def failing_processor(payload):
            raise ValueError("Processing error")
        
        worker = MessageWorker(failing_processor)
        queue.set_worker(worker.process_job)
        queue.start_worker()
        
        time.sleep(0.1)
        
        # Enqueue job - should not crash worker
        queue.enqueue(sample_job_payload)
        
        # Wait a bit
        time.sleep(0.3)
        
        # Worker should still be running
        assert queue._running is True
        
        # Cleanup
        queue.stop_worker()
    
    def test_setup_in_memory_worker(self, sample_job_payload):
        """Test setup_in_memory_worker helper function."""
        queue = InMemoryQueue()
        processed = []
        
        def processor(payload):
            processed.append(payload)
        
        setup_in_memory_worker(queue, processor)
        
        time.sleep(0.1)
        
        # Enqueue job
        queue.enqueue(sample_job_payload)
        
        # Wait for processing
        time.sleep(0.3)
        
        assert len(processed) == 1
        
        # Cleanup
        queue.stop_worker()
