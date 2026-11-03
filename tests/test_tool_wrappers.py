from pathlib import Path
from src.tool_wrappers import (
    is_tool_installed,
    parse_samtools_flagstat,
    run_native_biopython_qc,
    run_native_biopython_alignment,
    execute_sample_wrapper,
)


def test_is_tool_installed():
    # python executable is guaranteed to exist in path
    assert is_tool_installed("python") is True
    assert is_tool_installed("non_existent_biotool_98765") is False


def test_parse_samtools_flagstat():
    sample_flagstat = """
    1000000 + 0 in total (QC-passed reads + QC-failed reads)
    985420 + 0 mapped (98.54% : N/A)
    25000 + 0 duplicates
    """
    metrics = parse_samtools_flagstat(sample_flagstat)
    assert metrics["total_reads"] == 1000000
    assert metrics["mapped_reads"] == 985420
    assert metrics["mapped_percentage"] == 98.54
    assert metrics["duplication_rate_percent"] == 2.5


def test_native_biopython_qc(tmp_path):
    fastq_file = tmp_path / "test_sample.fastq"
    fastq_content = (
        "@READ1\n"
        "GCGCGCGCGCGCGCGC\n"
        "+\n"
        "IIIIIIIIIIIIIIII\n"
        "@READ2\n"
        "ATATATATATATATAT\n"
        "+\n"
        "IIIIIIIIIIIIIIII\n"
    )
    fastq_file.write_text(fastq_content, encoding="utf-8")

    qc = run_native_biopython_qc(fastq_file)
    assert qc["tool"] == "FastQC_Native"
    assert qc["total_reads"] == 2
    assert qc["gc_content_percent"] == 50.0  # 16 GC + 16 AT = 50%
    assert qc["mean_phred_quality"] == 40.0  # 'I' is Phred 40
    assert qc["adapter_content_flag"] == "PASS"


def test_native_biopython_alignment(tmp_path):
    fastq_file = tmp_path / "align_sample.fastq"
    fastq_file.write_text(
        "@READ1\nACGTACGTACGT\n+\nIIIIIIIIIIII\n", encoding="utf-8"
    )
    align = run_native_biopython_alignment(fastq_file)
    assert align["tool"] == "BWA/SAMtools_Native"
    assert align["total_reads"] == 1
    assert align["mapped_reads"] == 1
    assert align["mapped_percentage"] == 100.0


def test_execute_sample_wrapper_simulation():
    res = execute_sample_wrapper(
        sample_id="Sim_Sample",
        fastq_path=Path("dummy.fastq"),
        mode="simulation",
    )
    assert res["sample_id"] == "Sim_Sample"
    assert res["execution_mode"] == "simulation"
    assert "mean_phred_quality" in res
    assert "mapped_percentage" in res


def test_execute_sample_wrapper_real(tmp_path):
    fastq_file = tmp_path / "real_sample.fastq"
    fastq_file.write_text(
        "@R1\nCGCGCGCG\n+\nIIIIIIII\n", encoding="utf-8"
    )
    res = execute_sample_wrapper(
        sample_id="Real_Sample",
        fastq_path=fastq_file,
        mode="real",
        output_dir=tmp_path / "results",
    )
    assert res["sample_id"] == "Real_Sample"
    assert res["execution_mode"] == "real"
    assert res["total_reads"] == 1
    assert res["gc_content_percent"] == 100.0

