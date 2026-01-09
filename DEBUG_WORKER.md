# Worker Debugging Guide

## Issue: Messages Enqueued But Not Processed

### Symptoms
- Logs show: `"Message enqueued for processing"` ✅
- But NO logs from worker: `"Worker picked up job"`, `"Processing message job"`, etc. ❌
- No WhatsApp responses received

### Enhanced Logging Added

I've added comprehensive logging to help diagnose the issue:

1. **Queue enqueue**: Now logs queue size, worker status, callback status
2. **Worker startup**: Logs when worker thread starts
3. **Worker loop**: Logs when jobs are picked up
4. **Error handling**: Better exception logging

### What to Check

1. **Check startup logs** for:
   ```
   INFO: In-memory queue worker started for local development
   INFO: Worker thread started and running
   ```

2. **After sending a message**, check for:
   ```
   INFO: Job enqueued to in-memory queue (with queue_size, worker_running, has_worker_callback)
   INFO: Worker picked up job from queue
   INFO: Processing message job
   INFO: Starting message processing
   INFO: Processing WhatsApp message
   ```

3. **If worker logs are missing**, check:
   - Is the worker thread actually starting?
   - Is the callback set correctly?
   - Are exceptions being silently caught?

### Quick Test

Restart your Flask server and watch the logs. You should see:
1. Worker startup messages
2. When a message is enqueued, you should see worker pickup logs within 1-2 seconds

### Common Issues

1. **Worker not starting**: Check if `setup_in_memory_worker()` is being called
2. **Worker dying silently**: Check for exceptions in logs
3. **Queue timeout**: Worker uses 1-second timeout - this is normal when queue is empty


