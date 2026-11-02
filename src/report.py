import os
import sys
import datetime
from pathlib import Path
from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from jinja2 import Template

# Ensure UTF-8 output on Windows consoles to prevent charmap UnicodeEncodeErrors
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name }} - Execution Report</title>
    <style>
        :root {
            --primary-color: #2b5c8f;
            --secondary-color: #4a90e2;
            --accent-color: #28a745;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #2d3748;
            --text-muted: #718096;
            --border-color: #e2e8f0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            padding: 30px 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            margin: 0 0 10px 0;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .header p {
            margin: 0;
            font-size: 14px;
            opacity: 0.9;
        }

        .container {
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 20px;
        }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .kpi-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        }

        .kpi-card .value {
            font-size: 28px;
            font-weight: bold;
            color: var(--primary-color);
            margin: 5px 0;
        }

        .kpi-card .label {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }

        .section {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        }

        .section h2 {
            margin-top: 0;
            font-size: 20px;
            color: #1a202c;
            border-bottom: 2px solid #edf2f7;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 12px;
            border-top: 1px solid var(--border-color);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧬 ClawBio-Pipeline: Automated Multi-Omics Workflow Orchestrator</h1>
        <p><strong>Project:</strong> {{ project_name }} &nbsp;|&nbsp; <strong>Generated:</strong> {{ generated_date }}</p>
    </div>

    <div class="container">
        <!-- KPI Metrics Overview -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="label">Total Samples</div>
                <div class="value">{{ total_samples }}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Average Phred Score</div>
                <div class="value">{{ avg_phred }}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Mean Mapping Rate</div>
                <div class="value">{{ avg_mapping }}%</div>
            </div>
            <div class="kpi-card">
                <div class="label">Total Reads Analyzed</div>
                <div class="value">{{ total_reads_formatted }}</div>
            </div>
        </div>

        <!-- Section 1: QC Status Summary Chart -->
        <div class="section">
            <h2>Quality Control Checkpoints (Simulated FastQC)</h2>
            {{ qc_chart_html | safe }}
        </div>

        <!-- Section 2: Alignment Percentage Distribution -->
        <div class="section">
            <h2>Read Alignment Distribution (Simulated BWA / SAMtools)</h2>
            {{ align_chart_html | safe }}
        </div>

        <!-- Section 3: Detailed Metrics Table -->
        <div class="section">
            <h2>Detailed Metrics & Results Table</h2>
            {{ table_chart_html | safe }}
        </div>
    </div>

    <div class="footer">
        Generated by <strong>ClawBio-Pipeline</strong> • Modular Bioinformatics Orchestration Framework
    </div>
</body>
</html>
"""


def generate_html_report(
    metrics_df: pd.DataFrame,
    output_dir: str = "results",
    project_name: str = "Ovarian Cancer WGS Study",
) -> str:
    """Generates an interactive HTML report using Plotly and Jinja2.

    Args:
        metrics_df: DataFrame containing pipeline QC and alignment metrics.
        output_dir: Directory where the output HTML report will be saved.
        project_name: Name of the project to display in the report header.

    Returns:
        Absolute path to the generated HTML report.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. QC Status Summary Chart
    # Melt DataFrame for plotting Pass/Warn/Fail flags across metrics
    qc_long = metrics_df.melt(
        id_vars=["sample_id"],
        value_vars=["adapter_content_flag", "per_base_sequence_quality"],
        var_name="qc_metric",
        value_name="status",
    )

    color_map = {"PASS": "#2ca02c", "WARN": "#ff7f0e", "FAIL": "#d62728"}
    fig_qc = px.bar(
        qc_long,
        x="sample_id",
        y="status",
        color="status",
        facet_col="qc_metric",
        title="Quality Control Summary by Metric and Sample",
        labels={"status": "QC Status", "sample_id": "Sample ID", "qc_metric": "Metric"},
        color_discrete_map=color_map,
        category_orders={"status": ["PASS", "WARN", "FAIL"]},
    )
    fig_qc.update_layout(
        margin=dict(l=40, r=40, t=50, b=40),
        plot_bgcolor="#fcfcfc",
    )

    # 2. Alignment Percentage Distribution Chart
    if len(metrics_df) == 1:
        sample_data = metrics_df.iloc[0]
        fig_align = go.Figure(
            data=[
                go.Pie(
                    labels=["Mapped Reads", "Unmapped Reads"],
                    values=[
                        sample_data["mapped_reads"],
                        sample_data["total_reads"] - sample_data["mapped_reads"],
                    ],
                    hole=0.35,
                    title=f"Alignment: {sample_data['sample_id']}",
                    marker=dict(colors=["#2b5c8f", "#e2e8f0"]),
                )
            ]
        )
    else:
        # Multi-sample donut subplot visualization
        cols = len(metrics_df)
        specs = [[{"type": "domain"} for _ in range(cols)]]
        fig_align = make_subplots(
            rows=1,
            cols=cols,
            specs=specs,
            subplot_titles=[str(sid) for sid in metrics_df["sample_id"]],
        )

        for idx, (_, sample_data) in enumerate(metrics_df.iterrows(), start=1):
            fig_align.add_trace(
                go.Pie(
                    labels=["Mapped Reads", "Unmapped Reads"],
                    values=[
                        sample_data["mapped_reads"],
                        sample_data["total_reads"] - sample_data["mapped_reads"],
                    ],
                    hole=0.35,
                    name=sample_data["sample_id"],
                    marker=dict(colors=["#2b5c8f", "#cbd5e1"]),
                ),
                row=1,
                col=idx,
            )

    fig_align.update_layout(
        title_text="Alignment Distribution (Mapped vs. Unmapped Reads)",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    # 3. Interactive Data Table
    table_figure = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[f"<b>{col}</b>" for col in metrics_df.columns],
                    fill_color="#2b5c8f",
                    font=dict(color="white", size=12),
                    align="left",
                ),
                cells=dict(
                    values=[metrics_df[col] for col in metrics_df.columns],
                    fill_color="#f1f5f9",
                    font=dict(color="#1e293b", size=11),
                    height=28,
                    align="left",
                ),
            )
        ]
    )
    table_figure.update_layout(margin=dict(l=0, r=0, t=10, b=10))

    # Convert Plotly figures to HTML snippet
    qc_chart_html = fig_qc.to_html(full_html=False, include_plotlyjs="cdn")
    align_chart_html = fig_align.to_html(full_html=False, include_plotlyjs=False)
    table_chart_html = table_figure.to_html(full_html=False, include_plotlyjs=False)

    # Calculate summary statistics for header cards
    total_samples = len(metrics_df)
    avg_phred = (
        round(metrics_df["mean_phred_quality"].mean(), 2)
        if "mean_phred_quality" in metrics_df.columns
        else "N/A"
    )
    avg_mapping = (
        round(metrics_df["mapped_percentage"].mean(), 2)
        if "mapped_percentage" in metrics_df.columns
        else "N/A"
    )
    total_reads = (
        metrics_df["total_reads"].sum()
        if "total_reads" in metrics_df.columns
        else 0
    )
    total_reads_formatted = (
        f"{total_reads / 1e6:.1f}M" if total_reads >= 1e6 else f"{total_reads:,}"
    )

    template = Template(REPORT_HTML_TEMPLATE)
    html_content = template.render(
        project_name=project_name,
        generated_date=datetime.date.today().isoformat(),
        total_samples=total_samples,
        avg_phred=avg_phred,
        avg_mapping=avg_mapping,
        total_reads_formatted=total_reads_formatted,
        qc_chart_html=qc_chart_html,
        align_chart_html=align_chart_html,
        table_chart_html=table_chart_html,
    )

    report_path = out_path / "execution_report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Interactive HTML report generated at: {report_path.resolve()}")
    return str(report_path.resolve())

