import time
import json
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
        self.start_times: Dict[str, float] = {}

    def start_timer(self, operation: str) -> None:
        self.start_times[operation] = time.time()

    def end_timer(self, operation: str, metadata: Dict[str, Any] = None) -> float:
        if operation not in self.start_times:
            logger.warning(f"No start time found for operation: {operation}")
            return 0.0

        duration = time.time() - self.start_times[operation]
        del self.start_times[operation]

        metric = {
            "operation": operation,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self.metrics.append(metric)
        logger.info(f"Operation {operation} completed in {duration:.3f}s")
        return duration

    def get_metrics(self, operation: str = None) -> List[Dict[str, Any]]:
        if operation:
            return [m for m in self.metrics if m["operation"] == operation]
        return self.metrics.copy()

    def get_average_duration(self, operation: str) -> float:
        op_metrics = self.get_metrics(operation)
        if not op_metrics:
            return 0.0

        total_duration = sum(m["duration_seconds"] for m in op_metrics)
        return total_duration / len(op_metrics)

    def get_stats(self) -> Dict[str, Any]:
        if not self.metrics:
            return {"total_operations": 0}

        operations = {}
        for metric in self.metrics:
            op = metric["operation"]
            if op not in operations:
                operations[op] = []
            operations[op].append(metric["duration_seconds"])

        stats = {"total_operations": len(self.metrics), "operations": {}}

        for op, durations in operations.items():
            stats["operations"][op] = {
                "count": len(durations),
                "average_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations),
            }

        return stats

    def clear_metrics(self) -> None:
        self.metrics.clear()
        self.start_times.clear()

    def export_metrics(self, filename: str) -> None:
        try:
            with open(filename, "w") as f:
                json.dump(
                    {
                        "metrics": self.metrics,
                        "stats": self.get_stats(),
                        "exported_at": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
            logger.info(f"Metrics exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")


# Global metrics instance
performance_metrics = PerformanceMetrics()


def track_performance(operation: str):
    """Decorator to track performance of functions"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            performance_metrics.start_timer(operation)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                performance_metrics.end_timer(operation)

        def sync_wrapper(*args, **kwargs):
            performance_metrics.start_timer(operation)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                performance_metrics.end_timer(operation)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
