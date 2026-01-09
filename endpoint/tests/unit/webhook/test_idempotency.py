"""Unit tests for idempotency store."""

import pytest
import time
from endpoint.webhook.idempotency import (
    InMemoryIdempotencyStore,
    IdempotencyStore
)


class TestInMemoryIdempotencyStore:
    """Tests for InMemoryIdempotencyStore."""
    
    def test_is_duplicate_new_message(self):
        """Test checking duplicate for new message."""
        store = InMemoryIdempotencyStore()
        
        result = store.is_duplicate("msg123")
        
        assert result is False
    
    def test_is_duplicate_after_marking(self):
        """Test checking duplicate after marking as processed."""
        store = InMemoryIdempotencyStore()
        
        store.mark_processed("msg123")
        result = store.is_duplicate("msg123")
        
        assert result is True
    
    def test_is_duplicate_expired(self):
        """Test checking duplicate for expired message."""
        store = InMemoryIdempotencyStore()
        
        # Mark with very short TTL
        store.mark_processed("msg123", ttl_seconds=0.1)
        
        # Wait for expiration
        time.sleep(0.2)
        
        result = store.is_duplicate("msg123")
        
        assert result is False
    
    def test_mark_processed_with_ttl(self):
        """Test marking message as processed with TTL."""
        store = InMemoryIdempotencyStore()
        
        store.mark_processed("msg123", ttl_seconds=60)
        
        assert store.is_duplicate("msg123") is True
    
    def test_clear_store(self):
        """Test clearing idempotency store."""
        store = InMemoryIdempotencyStore()
        
        store.mark_processed("msg123")
        assert store.is_duplicate("msg123") is True
        
        store.clear()
        assert store.is_duplicate("msg123") is False
    
    def test_multiple_messages(self):
        """Test handling multiple different messages."""
        store = InMemoryIdempotencyStore()
        
        store.mark_processed("msg1")
        store.mark_processed("msg2")
        
        assert store.is_duplicate("msg1") is True
        assert store.is_duplicate("msg2") is True
        assert store.is_duplicate("msg3") is False
    
    def test_thread_safety(self):
        """Test thread safety of idempotency store."""
        import threading
        
        store = InMemoryIdempotencyStore()
        results = []
        
        def mark_and_check(msg_id):
            store.mark_processed(msg_id)
            results.append(store.is_duplicate(msg_id))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=mark_and_check, args=(f"msg{i}",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All should be True
        assert all(results)
        assert len(results) == 10
