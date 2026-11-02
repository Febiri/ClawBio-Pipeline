import random
from typing import Dict, Any

# NOTE: This module simulates the outputs of real bioinformatics tools
# for demonstration purposes.


def simulate_fastqc(sample_id: str) -> Dict[str, Any]:
    """Simulates FastQC statistics for a FASTQ file.

    Generates realistic metrics including mean Phred quality score, GC content percentage,
    adapter contamination flag, and per-base sequence quality flag.

    Args:
        sample_id: Identifier of the sample being analyzed.

    Returns:
        Dict of simulated FastQC quality metrics.
    """
    mean_quality = random.uniform(28.0, 38.0)
    gc_content = random.uniform(40.0, 60.0)

    return {
        "sample_id": sample_id,
        "tool": "FastQC_Sim",
        "mean_phred_quality": round(mean_quality, 2),
        "gc_content_percent": round(gc_content, 2),
        "adapter_content_flag": "PASS" if random.random() > 0.05 else "WARN",
        "per_base_sequence_quality": "PASS" if mean_quality > 30 else "WARN",
    }


def simulate_alignment_summary(sample_id: str) -> Dict[str, Any]:
    """Simulates BAM alignment summary statistics (e.g. BWA / SAMtools output).

    Generates realistic metrics including total reads, mapped reads, alignment percentage,
    and duplication rate.

    Args:
        sample_id: Identifier of the sample being analyzed.

    Returns:
        Dict of simulated BAM alignment summary statistics.
    """
    total_reads = 100000000  # 100 Million
    mapped_reads = total_reads * random.uniform(0.95, 0.995)

    return {
        "sample_id": sample_id,
        "tool": "BWA/SAMtools_Sim",
        "total_reads": total_reads,
        "mapped_reads": int(mapped_reads),
        "mapped_percentage": round((mapped_reads / total_reads) * 100, 2),
        "duplication_rate_percent": round(random.uniform(1.0, 5.0), 2),
    }

