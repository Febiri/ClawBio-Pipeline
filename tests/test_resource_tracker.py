import time
from src.resource_tracker import ResourceTracker


def test_resource_tracker_context():
    sample_id = "Sample_Tracking_01"
    with ResourceTracker(sample_id) as tracker:
        time.sleep(0.05)
        # Perform some memory allocation
        _ = [i * 2 for i in range(100000)]

    metrics = tracker.get_metrics()
    assert metrics["execution_time_sec"] >= 0.04
    assert metrics["peak_ram_mb"] > 0
    assert "cpu_percent" in metrics
    assert "worker_id" in metrics


def test_resource_tracker_start_stop():
    tracker = ResourceTracker("Manual_Sample")
    tracker.start()
    time.sleep(0.02)
    metrics = tracker.stop()

    assert metrics["execution_time_sec"] >= 0.01
    assert metrics["peak_ram_mb"] > 0

