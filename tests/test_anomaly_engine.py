from src.anomaly_engine import AnomalyDetector, DEFAULT_QC_THRESHOLDS


def test_anomaly_detector_optimal():
    detector = AnomalyDetector()
    optimal_metrics = {
        "mapped_percentage": 98.5,
        "gc_content_percent": 41.5,
        "mean_phred_quality": 36.0,
        "adapter_content_flag": "PASS",
        "duplication_rate_percent": 2.5,
    }
    result = detector.evaluate_sample(optimal_metrics)
    assert result["is_anomaly"] is False
    assert result["anomaly_severity"] == "PASS"
    assert len(result["anomaly_flags"]) == 0
    assert "Optimal Sequencing Quality" in result["status_label"]


def test_anomaly_detector_low_mapping():
    detector = AnomalyDetector()
    low_mapping = {
        "mapped_percentage": 88.0,
        "gc_content_percent": 41.0,
        "mean_phred_quality": 35.0,
        "adapter_content_flag": "PASS",
        "duplication_rate_percent": 3.0,
    }
    result = detector.evaluate_sample(low_mapping)
    assert result["is_anomaly"] is True
    assert result["anomaly_severity"] == "CRITICAL"
    assert any("Low Mapping Rate" in f for f in result["anomaly_flags"])
    assert len(result["insights"]) > 0


def test_anomaly_detector_gc_bias():
    detector = AnomalyDetector()
    gc_bias = {
        "mapped_percentage": 97.0,
        "gc_content_percent": 58.0,  # Dev > 10% from 41%
        "mean_phred_quality": 34.0,
        "adapter_content_flag": "PASS",
        "duplication_rate_percent": 3.0,
    }
    result = detector.evaluate_sample(gc_bias)
    assert result["is_anomaly"] is True
    assert any("GC Bias Detected" in f for f in result["anomaly_flags"])


def test_anomaly_detector_low_quality_and_adapter():
    detector = AnomalyDetector()
    poor_sample = {
        "mapped_percentage": 96.0,
        "gc_content_percent": 42.0,
        "mean_phred_quality": 22.0,  # Critical quality drop
        "adapter_content_flag": "FAIL",
        "duplication_rate_percent": 12.0,  # Elevated duplication
    }
    result = detector.evaluate_sample(poor_sample)
    assert result["is_anomaly"] is True
    assert result["anomaly_severity"] == "CRITICAL"
    assert len(result["anomaly_flags"]) >= 3

