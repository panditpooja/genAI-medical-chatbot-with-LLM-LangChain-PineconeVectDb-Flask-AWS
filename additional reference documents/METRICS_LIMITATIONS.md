# Metrics Tracking Limitations & Considerations

## Current Implementation

The global `metrics_tracker` instance works correctly for:

✅ **Single-process deployments** (Flask dev server)
✅ **Multi-threaded requests** (thread-safe with locks)
✅ **Single-worker production** (gunicorn/uwsgi with 1 worker)

## Limitations

### ⚠️ Multi-Process/Worker Deployments

**Problem**: When using multiple workers (e.g., `gunicorn -w 4`), each worker process has its own Python interpreter and thus its own `metrics_tracker` instance.

**Impact**:
- Metrics are **NOT aggregated** across workers
- Each `/metrics` endpoint call shows metrics only for the worker that handled that request
- You'll see different metrics depending on which worker handles the request
- Total request count will be split across workers

**Example**: If you have 4 workers and 100 requests:
- Worker 1 might handle 25 requests → shows 25 samples
- Worker 2 might handle 25 requests → shows 25 samples
- Worker 3 might handle 25 requests → shows 25 samples
- Worker 4 might handle 25 requests → shows 25 samples
- Each worker's `/metrics` endpoint shows only its own 25 samples

### ⚠️ No Persistence

- Metrics are stored **in-memory only**
- Metrics are **lost on server restart**
- No historical data retention

### ⚠️ Memory Limits

- Maximum 10,000 samples per metric type (configurable)
- Old samples are automatically dropped when limit is reached

## Solutions for Production

### Option 1: Single Worker (Simple)
```bash
gunicorn -w 1 app:app
```
- All metrics in one place
- Simple but limits scalability

### Option 2: Shared Storage (Recommended for Production)

Use Redis, a database, or a shared file to aggregate metrics across workers:

```python
# Example with Redis
import redis
import json

class RedisMetricsTracker:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "metrics:"
    
    def record_total_latency(self, latency_seconds: float):
        self.redis.lpush(f"{self.key_prefix}total", latency_seconds)
        self.redis.ltrim(f"{self.key_prefix}total", 0, 9999)  # Keep last 10k
    
    def get_metrics(self):
        total_samples = [float(x) for x in self.redis.lrange(f"{self.key_prefix}total", 0, -1)]
        # ... compute percentiles
```

### Option 3: External Monitoring

Use dedicated monitoring tools:
- **Prometheus + Grafana**: Industry standard
- **Datadog/New Relic**: Commercial APM solutions
- **CloudWatch/Stackdriver**: Cloud provider monitoring

### Option 4: Periodic Aggregation Script

Create a script that periodically:
1. Queries all worker endpoints
2. Aggregates metrics
3. Stores in shared location

## Current Behavior

The current implementation:
- ✅ Tracks metrics correctly per worker
- ✅ Shows worker/process ID in metrics output
- ✅ Thread-safe for concurrent requests
- ⚠️ Does NOT aggregate across workers
- ⚠️ Metrics reset on restart

## Recommendations

For **development/testing**: Current implementation is fine.

For **production with multiple workers**: 
1. Use shared storage (Redis recommended)
2. Or use external monitoring (Prometheus/Grafana)
3. Or aggregate metrics periodically via script

## Checking Your Deployment

To see if you're running multiple workers:
```bash
# Check process count
ps aux | grep gunicorn | wc -l

# Check gunicorn config
gunicorn --help | grep workers
```

The `/metrics` endpoint will show `worker_id` and `process_id` to help identify which worker you're querying.

