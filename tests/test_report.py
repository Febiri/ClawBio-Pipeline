from pathlib import Path
import pandas as pd
from src.report import generate_html_report


def test_generate_html_report_single_sample(tmp_path):
    data = [
        {
            "sample_id": "Tumor_1",
            "tool": "FastQC_Sim",
            "mean_phred_quality": 35.5,
            "gc_content_percent": 52.0,
            "adapter_content_flag": "PASS",
            "per_base_sequence_quality": "PASS",
            "total_reads": 100000000,
            "mapped_reads": 98000000,
            "mapped_percentage": 98.0,
            "duplication_rate_percent": 2.5,
        }
    ]
    df = pd.DataFrame(data)
    out_dir = tmp_path / "results"

    report_path = generate_html_report(
        df, output_dir=str(out_dir), project_name="Test Project"
    )

    report_file = Path(report_path)
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Test Project" in content
    assert "Tumor_1" in content
    assert "Quality Control Checkpoints" in content
    assert "Read Alignment Distribution" in content
    assert "Detailed Metrics &amp; Results Table" in content or "Detailed Metrics & Results Table" in content


def test_generate_html_report_multi_sample(tmp_path):
    data = [
        {
            "sample_id": "Sample_A",
            "mean_phred_quality": 36.2,
            "gc_content_percent": 48.0,
            "adapter_content_flag": "PASS",
            "per_base_sequence_quality": "PASS",
            "total_reads": 100000000,
            "mapped_reads": 97000000,
            "mapped_percentage": 97.0,
            "duplication_rate_percent": 3.0,
        },
        {
            "sample_id": "Sample_B",
            "mean_phred_quality": 29.5,
            "gc_content_percent": 51.5,
            "adapter_content_flag": "WARN",
            "per_base_sequence_quality": "WARN",
            "total_reads": 100000000,
            "mapped_reads": 96000000,
            "mapped_percentage": 96.0,
            "duplication_rate_percent": 4.1,
        },
    ]
    df = pd.DataFrame(data)
    out_dir = tmp_path / "multi_results"

    report_path = generate_html_report(
        df, output_dir=str(out_dir), project_name="Multi Sample Study"
    )

    report_file = Path(report_path)
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Multi Sample Study" in content
    assert "Sample_A" in content
    assert "Sample_B" in content

