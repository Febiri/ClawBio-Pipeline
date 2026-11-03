from pathlib import Path
from generate_sample_data import (
    generate_sequence,
    generate_phred_string,
    write_synthetic_fastq,
    generate_dataset,
)
from src.parser import validate_fastq


def test_generate_sequence():
    seq = generate_sequence(length=100, gc_target=0.40)
    assert len(seq) == 100
    assert set(seq).issubset({"A", "C", "G", "T"})


def test_generate_phred_string():
    qual = generate_phred_string(length=50, mean_quality=35.0)
    assert len(qual) == 50
    # Sanger Phred quality scores are >= '!' (ASCII 33)
    assert all(ord(c) >= 33 for c in qual)


def test_write_synthetic_fastq(tmp_path):
    fastq_file = tmp_path / "synthetic.fastq"
    write_synthetic_fastq(
        filepath=fastq_file,
        num_reads=20,
        read_length=100,
        gc_target=0.41,
        mean_quality=36.0,
    )
    assert fastq_file.exists()
    assert validate_fastq(fastq_file) is True


def test_generate_dataset(tmp_path):
    out_dir = tmp_path / "data" / "raw"
    cfg_file = tmp_path / "config.yaml"

    samples = generate_dataset(
        output_dir=str(out_dir),
        reads_per_sample=10,
        include_anomaly=True,
        update_config=True,
        config_path=str(cfg_file),
    )

    assert len(samples) == 3
    assert (out_dir / "Normal_Control_R1.fastq").exists()
    assert (out_dir / "Tumor_Biopsy_R1.fastq").exists()
    assert (out_dir / "Artifact_Sample_R1.fastq").exists()
    assert cfg_file.exists()

