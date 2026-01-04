"""
Utility script to view latency metrics.
Can be run independently or used to export metrics to a file.
"""
from src.metrics import metrics_tracker
import json
import sys


def main():
    """Display metrics summary."""
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Export as JSON
        metrics = metrics_tracker.get_metrics()
        print(json.dumps(metrics, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "--export":
        # Export full data to file
        filepath = sys.argv[2] if len(sys.argv) > 2 else "metrics_export.json"
        metrics_tracker.export_to_json(filepath)
        print(f"Metrics exported to {filepath}")
    else:
        # Display formatted summary
        print(metrics_tracker.get_summary())


if __name__ == "__main__":
    main()

