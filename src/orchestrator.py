import os
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import pandas as pd

from src.parser import load_config, get_pipeline_options
from src.resource_tracker import ResourceTracker
from src.anomaly_engine import AnomalyDetector
from src.tool_wrappers import execute_sample_wrapper
from src.variant_engine import call_and_annotate_variants
from src.clinical_agent import ClinicalInterpretationAgent
from src.report import generate_html_report
from src.cloud_storage import is_s3_uri, download_s3_file, upload_s3_file


def process_single_sample(
    sample_info: Dict[str, Any],
    mode: str = "simulation",
    output_dir: Path = Path("results"),
    reference_path: Optional[Path] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Processes a single genomic sample with QC, alignment, variants, and anomaly detection."""
    sample_id = sample_info.get("sample_id", "Unknown_Sample")
    raw_fastq = sample_info.get("raw_fastq", "")

    # Handle S3 URI download if necessary
    if is_s3_uri(raw_fastq):
        local_fastq = download_s3_file(raw_fastq)
    else:
        local_fastq = Path(raw_fastq)

    tracker = ResourceTracker(sample_id)
    with tracker:
        # Step 1: Execute QC and Alignment (Simulated or Real)
        raw_metrics = execute_sample_wrapper(
            sample_id=sample_id,
            fastq_path=local_fastq,
            mode=mode,
            output_dir=output_dir,
            reference_path=reference_path,
        )

        # Step 2: Call and Annotate Genomic Variants (ClinVar / ACMG)
        variants = call_and_annotate_variants(
            sample_id=sample_id,
            fastq_path=local_fastq,
            mode=mode,
            output_dir=output_dir / "variants",
        )

    # Step 3: Extract resource metrics
    resource_metrics = tracker.get_metrics()

    # Step 4: Run Biological Anomaly Engine
    detector = AnomalyDetector(thresholds=thresholds)
    anomaly_results = detector.evaluate_sample(raw_metrics)

    pathogenic_count = sum(
        1 for v in variants if v.get("clinvar_status") in ["Pathogenic", "Likely Pathogenic"]
    )

    combined = {
        **raw_metrics,
        **resource_metrics,
        **anomaly_results,
        "variant_count": len(variants),
        "pathogenic_variants": pathogenic_count,
        "sample_variants": variants,
    }
    return combined


def run_orchestration(
    config: Dict[str, Any] | str,
    mode: Optional[str] = None,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """Orchestrates parallel multi-sample bioinformatics execution across threads/processes."""
    if isinstance(config, (str, Path)):
        cfg = load_config(str(config))
    else:
        cfg = config

    opts = get_pipeline_options(cfg)
    project_name = opts["project_name"]
    exec_mode = mode or opts["execution_mode"]
    workers = max_workers or opts["max_workers"]
    output_dir = Path(opts["output_dir"])
    qc_thresholds = opts["qc_thresholds"]
    reference_path = Path(opts.get("reference_genome", "hg38"))
    if not reference_path.is_file():
        reference_path = None

    samples = cfg.get("samples", [])
    if not samples:
        raise ValueError("No samples defined in configuration.")

    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    # Parallel Execution with ThreadPoolExecutor
    total = len(samples)
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_sample = {
            executor.submit(
                process_single_sample,
                s,
                mode=exec_mode,
                output_dir=output_dir,
                reference_path=reference_path,
                thresholds=qc_thresholds,
            ): s.get("sample_id", "sample")
            for s in samples
        }

        for future in concurrent.futures.as_completed(future_to_sample):
            sample_id = future_to_sample[future]
            try:
                data = future.result()
                results.append(data)
            except Exception as e:
                # Capture failure gracefully
                results.append({
                    "sample_id": sample_id,
                    "is_anomaly": True,
                    "anomaly_severity": "CRITICAL",
                    "status_label": f"Execution Error: {str(e)}",
                    "anomaly_flags": [f"Pipeline Execution Failed: {str(e)}"],
                    "flags_summary": f"Error: {str(e)}",
                    "insights": ["Check FASTQ file readability or permissions."],
                    "execution_time_sec": 0.0,
                    "peak_ram_mb": 0.0,
                    "cpu_percent": 0.0,
                    "worker_id": "Error",
                    "variant_count": 0,
                    "pathogenic_variants": 0,
                    "sample_variants": [],
                })
            completed += 1
            if progress_callback:
                progress_callback(completed, total, sample_id)

    # Collect all variants across cohort
    all_variants: List[Dict[str, Any]] = []
    for r in results:
        all_variants.extend(r.get("sample_variants", []))

    # Run AI Clinical Interpretation Agent
    clinical_agent = ClinicalInterpretationAgent()
    clinical_summary = clinical_agent.analyze_variants(all_variants)

    metrics_df = pd.DataFrame(results)

    # Generate interactive HTML report with anomaly highlights, variants, and clinical insights
    report_path = generate_html_report(
        metrics_df,
        output_dir=str(output_dir),
        project_name=project_name,
        execution_mode=exec_mode,
        variants=all_variants,
        clinical_summary=clinical_summary,
    )

    # Optional cloud upload if destination S3 URI is specified in config
    s3_output_uri = cfg.get("s3_output_uri")
    if s3_output_uri and is_s3_uri(s3_output_uri):
        try:
            upload_s3_file(report_path, s3_output_uri)
        except Exception as e:
            print(f"Warning: Failed to upload report to S3: {e}")

    flagged_samples = [r for r in results if r.get("is_anomaly")]

    return {
        "project_name": project_name,
        "execution_mode": exec_mode,
        "total_samples": len(samples),
        "flagged_count": len(flagged_samples),
        "metrics_df": metrics_df,
        "report_path": report_path,
        "anomalies": flagged_samples,
        "variants": all_variants,
        "clinical_summary": clinical_summary,
    }
