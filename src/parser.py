import sys
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from Bio import SeqIO


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads the pipeline configuration YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Dict containing configuration parameters.

    Raises:
        SystemExit: If the file is not found or invalid.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            if not isinstance(config, dict):
                raise ValueError("Configuration YAML must contain a key-value mapping.")
            return config
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)


def get_sample_ids(config: Dict[str, Any]) -> List[str]:
    """Extracts sample IDs from configuration.

    Args:
        config: Parsed pipeline configuration dictionary.

    Returns:
        List of sample ID strings.
    """
    if "samples" not in config or not isinstance(config["samples"], list):
        return []
    return [sample["sample_id"] for sample in config["samples"] if "sample_id" in sample]


def get_pipeline_options(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts execution options and biological QC thresholds from config."""
    return {
        "project_name": config.get("project_name", "Bioinformatics Study"),
        "reference_genome": config.get("reference_genome", "hg38"),
        "execution_mode": config.get("execution_mode", "simulation"),
        "max_workers": config.get("max_workers", 4),
        "output_dir": config.get("output_dir", "results"),
        "qc_thresholds": config.get("qc_thresholds", {}),
    }


def validate_fastq(file_path: str | Path) -> bool:
    """Validates that a file is in valid FASTQ format using Biopython SeqIO.

    Args:
        file_path: Path to the FASTQ file.

    Returns:
        True if the file contains valid FASTQ records, False otherwise.
    """
    path = Path(file_path)
    if not path.is_file():
        return False

    try:
        with open(path, "r", encoding="utf-8") as handle:
            records = SeqIO.parse(handle, "fastq")
            # Verify that at least one valid record exists
            first_record = next(records, None)
            return first_record is not None
    except Exception:
        return False


def validate_samples(
    config: Dict[str, Any], base_dir: Optional[Path | str] = None
) -> Dict[str, bool]:
    """Validates raw FASTQ files for all samples in the configuration.

    Args:
        config: Parsed configuration dictionary.
        base_dir: Optional base directory to resolve relative paths against.

    Returns:
        Dictionary mapping sample_id to validation status (True/False).
    """
    base_path = Path(base_dir) if base_dir else Path.cwd()
    results = {}

    for sample in config.get("samples", []):
        sample_id = sample.get("sample_id", "unknown")
        raw_path = sample.get("raw_fastq")
        if not raw_path:
            results[sample_id] = False
            continue

        # Support cloud S3 URIs
        if isinstance(raw_path, str) and raw_path.startswith("s3://"):
            from src.cloud_storage import is_s3_uri
            results[sample_id] = is_s3_uri(raw_path) and len(raw_path.split("/")) >= 4
            continue

        resolved_path = (
            base_path / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)
        )
        results[sample_id] = validate_fastq(resolved_path)

    return results
