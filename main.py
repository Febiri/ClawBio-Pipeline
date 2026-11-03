import os
import sys
from pathlib import Path
from typing import Optional
import click
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text

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
from src.orchestrator import run_orchestration
from generate_sample_data import generate_dataset

console = Console()


def print_banner():
    banner = Text(
        "🧬 ClawBio-Pipeline: High-Throughput Bioinformatics Workflow Orchestrator\n"
        "Production-Grade Parallel QC, Alignment, Biological Anomaly Engine & Cloud API",
        style="bold cyan",
        justify="center",
    )
    console.print(Panel(banner, border_style="bright_blue"))


@click.group()
def cli():
    """ClawBio-Pipeline: Automated Multi-Omics Workflow Orchestrator."""
    pass


@cli.command()
@click.option(
    "--config", default="config.yaml", help="Path to pipeline configuration YAML."
)
@click.option(
    "--mode",
    type=click.Choice(["simulation", "real"], case_sensitive=False),
    default=None,
    help="Execution mode toggle: 'simulation' for rapid prototyping, 'real' for true tool wrappers.",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of concurrent worker threads for multi-sample parallel execution.",
)
@click.option(
    "--validate-raw/--no-validate-raw",
    default=True,
    help="Validate raw FASTQ files using Biopython SeqIO prior to execution.",
)
def run_pipeline(config: str, mode: Optional[str], workers: Optional[int], validate_raw: bool):
    """Executes the multi-sample bioinformatics workflow with parallel tracking & anomaly detection."""
    print_banner()

    # 1. Load Configuration
    cfg = parser.load_config(config)
    opts = parser.get_pipeline_options(cfg)
    project_name = opts["project_name"]
    exec_mode = mode or opts["execution_mode"]
    max_workers = workers or opts["max_workers"]

    console.print(f"🚀 Starting pipeline for project: {project_name}")

    info_table = Table(title="Pipeline Run Configuration", show_header=True, header_style="bold magenta")
    info_table.add_column("Parameter", style="cyan")
    info_table.add_column("Value", style="green")
    info_table.add_row("Project Name", project_name)
    info_table.add_row("Execution Mode", exec_mode.upper())
    info_table.add_row("Reference Genome", str(opts["reference_genome"]))
    info_table.add_row("Parallel Workers", str(max_workers))
    info_table.add_row("Output Directory", str(opts["output_dir"]))
    console.print(info_table)

    # 2. Extract Samples
    samples = parser.get_sample_ids(cfg)
    if not samples:
        console.print("[bold yellow]⚠️ Warning: No samples found in configuration.[/bold yellow]")
        return

    # 3. Validation Step
    if validate_raw:
        console.print("\n[bold blue]🔍 Validating Raw Sequence Inputs (Biopython SeqIO)...[/bold blue]")
        val_results = parser.validate_samples(cfg)
        val_table = Table(show_header=True, header_style="bold")
        val_table.add_column("Sample ID", style="cyan")
        val_table.add_column("Status", style="bold")

        all_valid = True
        for sid, is_valid in val_results.items():
            if is_valid:
                val_table.add_row(sid, "[green]✓ Valid FASTQ[/green]")
            else:
                val_table.add_row(sid, "[yellow]⚠️ Missing / Unverified File[/yellow]")
                if exec_mode == "real":
                    all_valid = False
        console.print(val_table)

        if exec_mode == "real" and not all_valid:
            console.print(
                "[bold red]❌ Execution halted: One or more FASTQ files are missing or invalid for real execution mode.[/bold red]"
            )
            return

    # 4. Multi-Sample Parallel Execution with Live Progress
    console.print(f"\n[bold blue]🚀 Starting Multi-Sample Execution across {max_workers} worker threads...[/bold blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing Samples...", total=len(samples))

        def on_progress(completed, total, sample_id):
            progress.update(task, completed=completed, description=f"[cyan]Completed {sample_id}")

        results = run_orchestration(
            config=cfg,
            mode=exec_mode,
            max_workers=max_workers,
            progress_callback=on_progress,
        )

    # 5. Output Summary Metrics Table
    df = results["metrics_df"]
    summary_table = Table(title="Execution Summary & Quality Control Results", show_header=True, header_style="bold blue")
    summary_table.add_column("Sample ID", style="bold white")
    summary_table.add_column("Mode", style="cyan")
    summary_table.add_column("Mapping %", justify="right")
    summary_table.add_column("GC %", justify="right")
    summary_table.add_column("Mean Phred", justify="right")
    summary_table.add_column("Variants", justify="right", style="magenta")
    summary_table.add_column("Time (s)", justify="right")
    summary_table.add_column("RAM (MB)", justify="right")
    summary_table.add_column("QC Status", style="bold")

    for _, row in df.iterrows():
        is_ano = row.get("is_anomaly", False)
        status_style = "[bold red]ANOMALY[/bold red]" if is_ano else "[bold green]PASS[/bold green]"
        mapping_str = f"{row.get('mapped_percentage', 0.0):.1f}%"
        gc_str = f"{row.get('gc_content_percent', 0.0):.1f}%"
        phred_str = f"Q{row.get('mean_phred_quality', 0.0):.1f}"
        var_count = str(row.get("variant_count", 0))
        time_str = f"{row.get('execution_time_sec', 0.0):.2f}s"
        ram_str = f"{row.get('peak_ram_mb', 0.0):.1f}"

        summary_table.add_row(
            str(row.get("sample_id")),
            str(row.get("execution_mode", exec_mode)),
            mapping_str,
            gc_str,
            phred_str,
            var_count,
            time_str,
            ram_str,
            status_style,
        )

    console.print(summary_table)

    # 6. Clinical Oncology Findings (2026 AI Agent)
    clinical_summary = results.get("clinical_summary", {})
    actionable_therapies = clinical_summary.get("actionable_therapies", [])
    if actionable_therapies:
        therapy_text = f"[bold white]{clinical_summary.get('clinical_narrative')}[/bold white]\n\n"
        for t in actionable_therapies:
            therapy_text += (
                f"• [bold magenta]{t['gene']}[/bold magenta] ({t['variant']}): "
                f"[bold cyan]{', '.join(t['recommended_drugs'][:2])}[/bold cyan] "
                f"[italic]({t['evidence_level']})[/italic]\n"
                f"  Trial: [blue]{t['matched_trial']}[/blue]\n"
            )

        console.print(Panel(
            therapy_text.strip(),
            title="🩺 AI Clinical Oncology Insight & Actionable Therapeutics (2026 Engine)",
            border_style="purple",
        ))

    # 7. Anomaly Engine Insights Highlight
    flagged = results.get("anomalies", [])
    if flagged:
        console.print(f"\n[bold red]⚠️ Biological Variant & Anomaly Alerts ({len(flagged)} sample(s) flagged):[/bold red]")
        for item in flagged:
            ano_panel = Panel(
                f"[bold red]Sample:[/bold red] {item.get('sample_id')}\n"
                f"[bold yellow]Severity:[/bold yellow] {item.get('anomaly_severity')}\n"
                f"[bold]Violations:[/bold] {item.get('flags_summary')}\n"
                f"[italic]💡 Insights: {' '.join(item.get('insights', []))}[/italic]",
                border_style="red",
                title=f"Anomaly Alert: {item.get('sample_id')}",
            )
            console.print(ano_panel)
    else:
        console.print("\n[bold green]✅ All samples passed automated biological QC checkpoints![/bold green]")

    # 7. Final Report Output
    report_file = results["report_path"]
    console.print(Panel(
        f"[bold green]Interactive HTML Report Generated Successfully![/bold green]\n"
        f"Path: [underline blue]{report_file}[/underline blue]",
        border_style="green",
    ))
    console.print("[bold green]✅ Pipeline execution complete.[/bold green]")


@cli.command()
@click.option(
    "--config", default="config.yaml", help="Path to pipeline configuration YAML."
)
def validate(config: str):
    """Validates configuration structure and sample FASTQ integrity."""
    print_banner()
    cfg = parser.load_config(config)
    project_name = cfg.get("project_name", "Unknown")
    console.print(f"[bold cyan]Checking configuration for project: {project_name}[/bold cyan]\n")

    results = parser.validate_samples(cfg)
    table = Table(title="Sample Verification Status", show_header=True, header_style="bold magenta")
    table.add_column("Sample ID", style="cyan")
    table.add_column("Integrity Status", style="bold")

    for sample_id, is_valid in results.items():
        status = "[bold green]PASSED[/bold green]" if is_valid else "[bold red]FAILED / NOT FOUND[/bold red]"
        table.add_row(sample_id, status)

    console.print(table)


@cli.command()
@click.option("--output-dir", default="data/raw", help="Target directory for synthetic FASTQ files.")
@click.option("--reads", type=int, default=150, help="Number of sequencing reads per sample.")
@click.option("--anomaly/--no-anomaly", default=True, help="Include an anomaly sample with biological artifacts.")
@click.option("--update-config/--no-update-config", default=True, help="Update config.yaml with generated samples.")
def generate_samples(output_dir: str, reads: int, anomaly: bool, update_config: bool):
    """Generates synthetic FASTQ files for rapid local testing without external data hunting."""
    print_banner()
    console.print("[bold cyan]Generating synthetic benchmark dataset...[/bold cyan]")
    generate_dataset(
        output_dir=output_dir,
        reads_per_sample=reads,
        include_anomaly=anomaly,
        update_config=update_config,
    )
    console.print("[bold green]✅ Dataset generation completed.[/bold green]")


@cli.command()
@click.option("--host", default="127.0.0.1", help="API host interface.")
@click.option("--port", type=int, default=8000, help="API server port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development.")
def serve(host: str, port: int, reload: bool):
    """Starts the FastAPI REST API and Cloud Orchestrator server."""
    print_banner()
    console.print(f"[bold green]Starting ClawBio-Pipeline REST API server on http://{host}:{port}...[/bold green]")
    console.print(f"[cyan]Interactive OpenAPI documentation available at http://{host}:{port}/docs[/cyan]")
    uvicorn.run("src.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
