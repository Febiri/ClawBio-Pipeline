#!/usr/bin/env python3
"""Synthetic FASTQ Data Generator for ClawBio-Pipeline.

Generates realistic paired or single-end FASTQ datasets with configurable
quality profiles, GC distributions, and biological anomalies (e.g. GC bias,
low base quality, adapter contamination) for immediate local benchmarking.
"""

import os
import random
import argparse
from pathlib import Path
import yaml


DNA_BASES = ["A", "C", "G", "T"]


def generate_sequence(length: int = 150, gc_target: float = 0.41) -> str:
    """Generates a random DNA sequence with a target GC content percentage."""
    gc_prob = gc_target / 2.0
    at_prob = (1.0 - gc_target) / 2.0
    weights = [at_prob, gc_prob, gc_prob, at_prob]
    return "".join(random.choices(DNA_BASES, weights=weights, k=length))


def generate_phred_string(length: int = 150, mean_quality: float = 36.0, std_dev: float = 3.0) -> str:
    """Generates ASCII-encoded Sanger Phred+33 quality scores."""
    scores = []
    for _ in range(length):
        score = int(random.gauss(mean_quality, std_dev))
        score = max(10, min(41, score))  # Clamp between Q10 and Q41
        scores.append(chr(score + 33))
    return "".join(scores)


def write_synthetic_fastq(
    filepath: Path,
    num_reads: int = 100,
    read_length: int = 150,
    gc_target: float = 0.41,
    mean_quality: float = 36.0,
    with_adapter: bool = False,
):
    """Writes synthetic reads to a FASTQ file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    sample_name = filepath.stem

    adapter_seed = "AGATCGGAAGAGCACACGTCT"

    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(1, num_reads + 1):
            read_id = f"@{sample_name}:{i}:FCCLAW:1:1101:{1000 + i}:{2000 + i}"
            seq = generate_sequence(read_length, gc_target)
            qual = generate_phred_string(read_length, mean_quality)

            if with_adapter and i % 5 == 0:
                # Inject adapter sequence
                seq = seq[: read_length - len(adapter_seed)] + adapter_seed

            f.write(f"{read_id}\n{seq}\n+\n{qual}\n")


def generate_dataset(
    output_dir: str = "data/raw",
    reads_per_sample: int = 150,
    include_anomaly: bool = True,
    update_config: bool = True,
    config_path: str = "config.yaml",
):
    """Generates a standard test cohort containing normal, tumor, and anomaly samples."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    samples = [
        {
            "sample_id": "Normal_Control_R1",
            "filename": "Normal_Control_R1.fastq",
            "gc": 0.41,
            "quality": 37.0,
            "adapter": False,
        },
        {
            "sample_id": "Tumor_Biopsy_R1",
            "filename": "Tumor_Biopsy_R1.fastq",
            "gc": 0.42,
            "quality": 35.5,
            "adapter": False,
        },
    ]

    if include_anomaly:
        samples.append(
            {
                "sample_id": "Artifact_Sample_R1",
                "filename": "Artifact_Sample_R1.fastq",
                "gc": 0.58,  # Significant GC bias (>10% dev from 41%)
                "quality": 23.5,  # Sub-optimal quality (< Q30)
                "adapter": True,  # High adapter contamination
            }
        )

    generated_samples = []
    print(f"🧬 Generating synthetic sequencing data in '{output_dir}'...")

    for s in samples:
        file_path = out_path / s["filename"]
        write_synthetic_fastq(
            filepath=file_path,
            num_reads=reads_per_sample,
            read_length=150,
            gc_target=s["gc"],
            mean_quality=s["quality"],
            with_adapter=s["adapter"],
        )
        print(f"  ✓ Created {s['sample_id']} -> {file_path} ({reads_per_sample} reads, GC: {int(s['gc']*100)}%)")
        generated_samples.append({
            "sample_id": s["sample_id"],
            "raw_fastq": str(file_path).replace("\\", "/"),
        })

    if update_config:
        cfg = {
            "project_name": "Multi-Sample WGS Benchmark Cohort",
            "reference_genome": "hg38",
            "execution_mode": "simulation",
            "max_workers": 4,
            "qc_thresholds": {
                "min_mapped_percentage": 95.0,
                "reference_gc_percent": 41.0,
                "max_gc_deviation": 10.0,
                "min_phred_quality": 30.0,
                "max_duplication_rate": 8.0,
            },
            "samples": generated_samples,
            "output_dir": "results",
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
        print(f"📄 Updated pipeline configuration at '{config_path}' with {len(generated_samples)} samples.")

    print("✨ Synthetic dataset generation completed successfully!")
    return generated_samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic FASTQ test files.")
    parser.add_argument("--output-dir", default="data/raw", help="Target directory for FASTQ files.")
    parser.add_argument("--reads", type=int, default=150, help="Number of reads per sample.")
    parser.add_argument("--no-anomaly", action="store_true", help="Exclude anomaly sample.")
    parser.add_argument("--no-config-update", action="store_true", help="Do not update config.yaml.")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path.")

    args = parser.parse_args()
    generate_dataset(
        output_dir=args.output_dir,
        reads_per_sample=args.reads,
        include_anomaly=not args.no_anomaly,
        update_config=not args.no_config_update,
        config_path=args.config,
    )

