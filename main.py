import sys
import click
import pandas as pd
from tqdm import tqdm

# Ensure UTF-8 output on Windows consoles to prevent charmap UnicodeEncodeErrors
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import src.parser as parser
import src.bio_tasks_simulator as simulator
import src.report as report


@click.group()
def cli():
    """ClawBio-Pipeline: Automated Bioinformatics Workflow Orchestrator."""
    pass


@cli.command()
@click.option(
    "--config", default="config.yaml", help="Path to pipeline configuration YAML."
)
@click.option(
    "--validate-raw/--no-validate-raw",
    default=True,
    help="Validate raw FASTQ files using Biopython SeqIO.",
)
def run_pipeline(config: str, validate_raw: bool):
    """Executes the simulated bioinformatics workflow."""

    # 1. Load Config
    cfg = parser.load_config(config)
    project_name = cfg.get("project_name", "Bioinformatics Study")
    click.echo(f"🚀 Starting pipeline for project: {project_name}")

    # 2. Define Samples
    samples = parser.get_sample_ids(cfg)
    if not samples:
        click.echo("⚠️ Warning: No samples found in configuration.")
        return

    # Validate raw data with Biopython SeqIO
    if validate_raw:
        click.echo("🔍 Validating raw FASTQ data using Biopython SeqIO...")
        validation_results = parser.validate_samples(cfg)
        for sid, is_valid in validation_results.items():
            status = "✓ Valid FASTQ" if is_valid else "⚠️ FASTQ missing or simulated"
            click.echo(f"   [{sid}] {status}")

    # 3. Execute Simulated Tasks
    all_metrics = []

    with tqdm(total=len(samples), desc="Processing Samples") as pbar:
        for sample in samples:
            # Step A: Simulate QC
            qc_stats = simulator.simulate_fastqc(sample)

            # Step B: Simulate Alignment
            alignment_stats = simulator.simulate_alignment_summary(sample)

            # Combine metrics
            combined = {**qc_stats, **alignment_stats}
            all_metrics.append(combined)
            pbar.update(1)

    # 4. Compile Metrics
    metrics_df = pd.DataFrame(all_metrics)

    # 5. Generate Report
    click.echo("📊 Generating final interactive HTML report...")
    output_dir = cfg.get("output_dir", "results")
    report.generate_html_report(
        metrics_df, output_dir=output_dir, project_name=project_name
    )

    click.echo("✅ Pipeline execution complete.")


@cli.command()
@click.option(
    "--config", default="config.yaml", help="Path to pipeline configuration YAML."
)
def validate(config: str):
    """Validates configuration structure and sample FASTQ integrity."""
    cfg = parser.load_config(config)
    click.echo(f"Checking configuration for: {cfg.get('project_name', 'Unknown')}")
    results = parser.validate_samples(cfg)
    for sample_id, is_valid in results.items():
        status = "PASSED" if is_valid else "FAILED / NOT FOUND"
        click.echo(f"  • Sample '{sample_id}': {status}")


if __name__ == "__main__":
    cli()

