from src.bio_tasks_simulator import simulate_fastqc, simulate_alignment_summary


def test_simulate_fastqc():
    sample_id = "Sample_Test_01"
    qc = simulate_fastqc(sample_id)

    assert qc["sample_id"] == sample_id
    assert qc["tool"] == "FastQC_Sim"
    assert 28.0 <= qc["mean_phred_quality"] <= 38.0
    assert 40.0 <= qc["gc_content_percent"] <= 60.0
    assert qc["adapter_content_flag"] in ["PASS", "WARN"]
    assert qc["per_base_sequence_quality"] in ["PASS", "WARN"]


def test_simulate_alignment_summary():
    sample_id = "Sample_Test_02"
    align = simulate_alignment_summary(sample_id)

    assert align["sample_id"] == sample_id
    assert align["tool"] == "BWA/SAMtools_Sim"
    assert align["total_reads"] == 100000000
    assert 95000000 <= align["mapped_reads"] <= 99500000
    assert 95.0 <= align["mapped_percentage"] <= 99.5
    assert 1.0 <= align["duplication_rate_percent"] <= 5.0

