import os
import time
import threading
import psutil
from typing import Dict, Any, Optional


class ResourceTracker:
    """Tracks CPU usage, peak RAM consumption, and execution time for pipeline samples."""

    def __init__(self, sample_id: str):
        self.sample_id = sample_id
        self.process = psutil.Process(os.getpid())
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.initial_ram_mb: float = 0.0
        self.peak_ram_mb: float = 0.0
        self.cpu_percent: float = 0.0
        self.worker_id: str = threading.current_thread().name

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        """Starts resource monitoring."""
        self.start_time = time.perf_counter()
        # Initialize CPU measurement
        self.process.cpu_percent(interval=None)
        mem_info = self.process.memory_info()
        self.initial_ram_mb = mem_info.rss / (1024 * 1024)
        self.peak_ram_mb = self.initial_ram_mb
        self.worker_id = threading.current_thread().name

    def stop(self) -> Dict[str, Any]:
        """Stops resource monitoring and calculates peak consumption."""
        self.end_time = time.perf_counter()
        mem_info = self.process.memory_info()
        current_ram_mb = mem_info.rss / (1024 * 1024)
        self.peak_ram_mb = max(self.peak_ram_mb, current_ram_mb)
        self.cpu_percent = self.process.cpu_percent(interval=None)

        duration = self.end_time - (self.start_time or self.end_time)

        return self.get_metrics(duration)

    def get_metrics(self, duration: Optional[float] = None) -> Dict[str, Any]:
        """Returns the collected resource metrics."""
        if duration is None:
            if self.start_time and self.end_time:
                duration = self.end_time - self.start_time
            else:
                duration = 0.0

        return {
            "execution_time_sec": round(max(0.01, duration), 3),
            "peak_ram_mb": round(self.peak_ram_mb, 2),
            "cpu_percent": round(self.cpu_percent, 1),
            "worker_id": self.worker_id,
        }

