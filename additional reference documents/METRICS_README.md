# Latency Metrics Tracking

This document describes the latency metrics tracking system for the medical chatbot.

## Metrics Tracked

1. **End-to-End Response Latency (`total_s`)**: Total time from request to response in seconds
   - Includes: retrieval time + LLM generation time + processing overhead
   - Measured from when the request is received until the response is ready

2. **Retrieval Latency (`retrieval_ms`)**: Time to retrieve documents from Pinecone in milliseconds
   - Includes: embedding generation + vector search + document retrieval
   - Measured only for RAG queries (not gratitude messages)

## Percentiles Computed

- **P50 (Median)**: 50th percentile - half of requests are faster, half are slower
- **P95**: 95th percentile - 95% of requests are faster than this value

## Usage

### View Metrics via Web Endpoint

1. **JSON Format**: `http://localhost:8080/metrics`
   - Returns JSON with P50/P95 values and sample counts

2. **Formatted Summary**: `http://localhost:8080/metrics/summary`
   - Returns human-readable formatted summary

### View Metrics via Command Line

```bash
# Display formatted summary
python view_metrics.py

# Export as JSON
python view_metrics.py --json

# Export full data to file
python view_metrics.py --export metrics.json
```

## Example Output

```
=== Latency Metrics ===
Total Samples: 150
Retrieval Samples: 145

End-to-End Response Latency (seconds):
  P50: 2.345s
  P95: 4.567s

Retrieval Latency (milliseconds):
  P50: 123.45ms
  P95: 234.56ms
```

## Implementation Details

- Metrics are stored in memory using thread-safe deques
- Maximum of 10,000 samples are kept (configurable)
- Metrics persist for the lifetime of the application
- Thread-safe for concurrent requests

## Files

- `src/metrics.py`: Metrics tracking module
- `src/retriever_wrapper.py`: Wrapper to track retrieval latency
- `view_metrics.py`: Command-line utility to view metrics
- `app.py`: Updated to track metrics on each request

