"""
Metrics tracking module for latency monitoring.
Tracks end-to-end response latency and retrieval latency.
"""
import time
from typing import List, Dict, Optional
from collections import deque
import threading
import json
import os


class MetricsTracker:
    """Thread-safe metrics tracker for latency measurements."""
    
    def __init__(self, max_samples: int = 10000):
        """
        Initialize metrics tracker.
        
        Args:
            max_samples: Maximum number of samples to keep in memory
        """
        self.max_samples = max_samples
        self.total_samples: deque = deque(maxlen=max_samples)  # End-to-end latency in seconds
        self.retrieval_samples: deque = deque(maxlen=max_samples)  # Retrieval latency in milliseconds
        self.lock = threading.Lock()
        # Track process/worker ID for multi-process deployments
        self.process_id = os.getpid()
        self.worker_id = os.environ.get('GUNICORN_WORKER_ID', f'process-{self.process_id}')
    
    def record_total_latency(self, latency_seconds: float):
        """Record end-to-end response latency in seconds."""
        with self.lock:
            self.total_samples.append(latency_seconds)
    
    def record_retrieval_latency(self, latency_ms: float):
        """Record retrieval latency in milliseconds."""
        with self.lock:
            self.retrieval_samples.append(latency_ms)
    
    def compute_percentile(self, data: List[float], percentile: float) -> Optional[float]:
        """
        Compute percentile value from a list of numbers.
        
        Args:
            data: List of numeric values
            percentile: Percentile to compute (0-100)
            
        Returns:
            Percentile value or None if data is empty
        """
        if not data:
            return None
        
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_metrics(self) -> Dict:
        """
        Get current metrics including P50 and P95 percentiles.
        
        Returns:
            Dictionary with metrics including:
            - total_s_p50: P50 end-to-end latency (seconds)
            - total_s_p95: P95 end-to-end latency (seconds)
            - retrieval_ms_p50: P50 retrieval latency (milliseconds)
            - retrieval_ms_p95: P95 retrieval latency (milliseconds)
            - total_count: Number of total latency samples
            - retrieval_count: Number of retrieval latency samples
            - worker_id: Process/worker identifier
            - process_id: OS process ID
        """
        with self.lock:
            total_list = list(self.total_samples)
            retrieval_list = list(self.retrieval_samples)
        
        metrics = {
            "total_s_p50": self.compute_percentile(total_list, 50),
            "total_s_p95": self.compute_percentile(total_list, 95),
            "retrieval_ms_p50": self.compute_percentile(retrieval_list, 50),
            "retrieval_ms_p95": self.compute_percentile(retrieval_list, 95),
            "total_count": len(total_list),
            "retrieval_count": len(retrieval_list),
            "worker_id": self.worker_id,
            "process_id": self.process_id,
        }
        
        return metrics
    
    def get_summary(self) -> str:
        """
        Get a formatted summary string of metrics.
        
        Returns:
            Formatted string with metrics summary
        """
        metrics = self.get_metrics()
        
        summary = "=== Latency Metrics ===\n"
        summary += f"Worker/Process ID: {metrics['worker_id']} (PID: {metrics['process_id']})\n"
        summary += f"Total Samples: {metrics['total_count']}\n"
        summary += f"Retrieval Samples: {metrics['retrieval_count']}\n\n"
        
        summary += "End-to-End Response Latency (seconds):\n"
        if metrics['total_s_p50'] is not None:
            summary += f"  P50: {metrics['total_s_p50']:.3f}s\n"
            summary += f"  P95: {metrics['total_s_p95']:.3f}s\n"
        else:
            summary += "  No data available\n"
        
        summary += "\nRetrieval Latency (milliseconds):\n"
        if metrics['retrieval_ms_p50'] is not None:
            summary += f"  P50: {metrics['retrieval_ms_p50']:.2f}ms\n"
            summary += f"  P95: {metrics['retrieval_ms_p95']:.2f}ms\n"
        else:
            summary += "  No data available\n"
        
        # Add warning for multi-process deployments
        summary += "\n⚠️  NOTE: These metrics are per-worker/process. "
        summary += "In multi-worker deployments, each worker tracks its own metrics.\n"
        
        return summary
    
    def export_to_json(self, filepath: str):
        """
        Export metrics to JSON file.
        
        Args:
            filepath: Path to save JSON file
        """
        metrics = self.get_metrics()
        with self.lock:
            metrics['total_samples'] = list(self.total_samples)
            metrics['retrieval_samples'] = list(self.retrieval_samples)
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.total_samples.clear()
            self.retrieval_samples.clear()


# Global metrics tracker instance
# NOTE: In multi-process deployments (e.g., gunicorn with multiple workers),
# each worker process will have its own instance. Metrics are NOT aggregated
# across processes. For production use, consider using shared storage (Redis, DB, etc.)
metrics_tracker = MetricsTracker()
