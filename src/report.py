import os
import sys
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
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
    <title>{{ project_name }} - Execution & Clinical Genomic Report</title>
    <style>
        :root {
            --primary-color: #1e3a8a;
            --secondary-color: #3b82f6;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
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
            background: linear-gradient(135deg, #090d16 0%, #1e3a8a 50%, #2563eb 100%);
            color: #ffffff;
            padding: 35px 40px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }

        .header h1 {
            margin: 0 0 8px 0;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        .header p {
            margin: 0;
            font-size: 14px;
            opacity: 0.9;
        }

        .mode-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.35);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .container {
            max-width: 1250px;
            margin: 30px auto;
            padding: 0 20px;
        }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 18px;
            margin-bottom: 30px;
        }

        .kpi-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px 15px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            transition: transform 0.15s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
        }

        .kpi-card .value {
            font-size: 26px;
            font-weight: 800;
            color: var(--primary-color);
            margin: 4px 0;
        }

        .kpi-card.anomaly-card .value {
            color: {{ '#ef4444' if flagged_count > 0 else '#10b981' }};
        }

        .kpi-card.variant-card .value {
            color: #8b5cf6;
        }

        .kpi-card .label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            font-weight: 600;
        }

        /* Clinical Therapy Section */
        .clinical-section {
            background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
            border: 2px solid #ddd6fe;
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.08);
        }

        .clinical-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .clinical-header h2 {
            margin: 0;
            font-size: 20px;
            color: #5b21b6;
        }

        .clinical-narrative {
            background: rgba(255, 255, 255, 0.9);
            border-left: 4px solid var(--accent-purple);
            padding: 14px 18px;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 20px;
            color: #334155;
            line-height: 1.6;
        }

        .therapy-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 16px;
        }

        .therapy-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }

        .therapy-card-title {
            font-size: 15px;
            font-weight: 700;
            color: #1e1b4b;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .badge-evidence {
            font-size: 11px;
            background: #e0e7ff;
            color: #3730a3;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }

        .therapy-detail {
            font-size: 13px;
            margin-bottom: 6px;
            color: #475569;
        }

        /* Anomaly Section */
        .anomaly-section {
            background: var(--card-bg);
            border: 2px solid {{ '#fca5a5' if flagged_count > 0 else '#a7f3d0' }};
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        }

        .anomaly-header h2 {
            margin: 0 0 16px 0;
            font-size: 20px;
            color: {{ '#b91c1c' if flagged_count > 0 else '#047857' }};
        }

        .anomaly-item {
            background: #fff5f5;
            border-left: 4px solid var(--accent-red);
            border-radius: 6px;
            padding: 16px 20px;
            margin-bottom: 14px;
        }

        .anomaly-item.warning {
            background: #fffbeb;
            border-left-color: var(--accent-amber);
        }

        .badge-severity {
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            color: #fff;
            background: var(--accent-red);
        }

        .badge-severity.warning {
            background: var(--accent-amber);
            color: #78350f;
        }

        .section {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        }

        .section h2 {
            margin-top: 0;
            font-size: 20px;
            color: #0f172a;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .footer {
            text-align: center;
            padding: 25px;
            color: var(--text-muted);
            font-size: 13px;
            border-top: 1px solid var(--border-color);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top">
            <div>
                <h1>🧬 ClawBio-Pipeline: Automated Multi-Omics Workflow Orchestrator</h1>
                <p><strong>Project:</strong> {{ project_name }} &nbsp;|&nbsp; <strong>Generated:</strong> {{ generated_date }}</p>
            </div>
            <div class="mode-badge">
                ⚙️ Mode: {{ execution_mode }}
            </div>
        </div>
    </div>

    <div class="container">
        <!-- KPI Metrics Overview -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="label">Total Samples</div>
                <div class="value">{{ total_samples }}</div>
            </div>
            <div class="kpi-card anomaly-card">
                <div class="label">Flagged Anomalies</div>
                <div class="value">{{ flagged_count }}</div>
            </div>
            <div class="kpi-card variant-card">
                <div class="label">Total Variants</div>
                <div class="value">{{ total_variants }}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Mean Mapping</div>
                <div class="value">{{ avg_mapping }}%</div>
            </div>
            <div class="kpi-card">
                <div class="label">Average Phred</div>
                <div class="value">Q{{ avg_phred }}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Peak RAM (Avg)</div>
                <div class="value">{{ avg_ram }} MB</div>
            </div>
        </div>

        <!-- AI Clinical Oncology & Actionable Therapeutics -->
        {% if clinical_data and clinical_data.actionable_therapies %}
        <div class="clinical-section">
            <div class="clinical-header">
                <h2>🩺 AI Clinical Oncology Insight & Actionable Therapeutics (2026 Engine)</h2>
            </div>
            <div class="clinical-narrative">
                {{ clinical_data.clinical_narrative }}
            </div>
            <div class="therapy-grid">
                {% for item in clinical_data.actionable_therapies %}
                <div class="therapy-card">
                    <div class="therapy-card-title">
                        <span><strong>{{ item.gene }}</strong> ({{ item.variant }})</span>
                        <span class="badge-evidence">{{ item.evidence_level.split(' ')[0] }}</span>
                    </div>
                    <div class="therapy-detail"><strong>Targeted Drugs:</strong> <span style="color:#2563eb; font-weight:600;">{{ item.recommended_drugs | join(', ') }}</span></div>
                    <div class="therapy-detail"><strong>Class:</strong> {{ item.therapy_class }}</div>
                    <div class="therapy-detail"><strong>Indication:</strong> {{ item.clinical_indication }}</div>
                    <div class="therapy-detail"><strong>Mechanism:</strong> {{ item.mechanism_of_action }}</div>
                    <div class="therapy-detail" style="color:#b91c1c;"><strong>Resistance:</strong> {{ item.resistance_profile }}</div>
                    <div class="therapy-detail" style="color:#4338ca; font-style:italic;"><strong>Trial Match:</strong> {{ item.matched_trial }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Smart Insight Engine: Biological Variant / Anomaly Detection -->
        <div class="anomaly-section">
            <div class="anomaly-header">
                <h2>⚠️ Automated Biological Variant & Anomaly Detection (Smart Insight Engine)</h2>
            </div>
            {% if flagged_count > 0 %}
                {% for item in anomaly_list %}
                <div class="anomaly-item {{ 'warning' if item.severity == 'WARNING' else '' }}">
                    <div style="font-weight:700; margin-bottom:6px;">
                        <span>Sample: <strong>{{ item.sample_id }}</strong></span>
                        <span class="badge-severity {{ 'warning' if item.severity == 'WARNING' else '' }}">{{ item.severity }}</span>
                        <span style="font-size:12px; font-weight:normal; color:#64748b;">{{ item.status_label }}</span>
                    </div>
                    <div style="font-size:13px; color:#475569; margin-bottom:6px;">
                        <strong>Rule Violations:</strong>
                        <ul>
                            {% for flag in item.flags %}
                            <li>{{ flag }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% if item.insights %}
                    <div style="font-size:13px; font-style:italic; background:rgba(255,255,255,0.7); padding:8px 12px; border-radius:4px;">
                        💡 <strong>Biological Insight & Recommendation:</strong> {{ item.insights | join(" ") }}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <div style="color: #065f46; font-weight: 600; padding: 10px 0;">
                    ✓ Optimal Quality: All samples passed automated biological checkpoints (Mapping Rate ≥ 95%, GC Deviation ≤ 10%, Phred Quality ≥ Q30).
                </div>
            {% endif %}
        </div>

        <!-- Section 1: Variant Calling & Annotation Table -->
        {% if variant_table_html %}
        <div class="section">
            <h2>🧬 Somatic & Germline Variant Calling (ClinVar / ACMG Annotation)</h2>
            {{ variant_table_html | safe }}
        </div>
        {% endif %}

        <!-- Section 2: Resource & Performance Tracking -->
        {% if resource_chart_html %}
        <div class="section">
            <h2>⚡ Multi-Sample Resource & Parallel Performance Tracking</h2>
            {{ resource_chart_html | safe }}
        </div>
        {% endif %}

        <!-- Section 3: QC Status Summary Chart -->
        <div class="section">
            <h2>Quality Control Checkpoints (FastQC Analysis)</h2>
            {{ qc_chart_html | safe }}
        </div>

        <!-- Section 4: Alignment Percentage Distribution -->
        <div class="section">
            <h2>Read Alignment Distribution (BWA / SAMtools Analysis)</h2>
            {{ align_chart_html | safe }}
        </div>

        <!-- Section 5: Detailed Metrics Table -->
        <div class="section">
            <h2>Detailed Metrics & Results Table</h2>
            {{ table_chart_html | safe }}
        </div>
    </div>

    <div class="footer">
        Generated by <strong>ClawBio-Pipeline</strong> • High-Throughput Computational Biology Orchestration Framework
    </div>
</body>
</html>
"""


def generate_html_report(
    metrics_df: pd.DataFrame,
    output_dir: str = "results",
    project_name: str = "Ovarian Cancer WGS Study",
    execution_mode: str = "simulation",
    variants: Optional[List[Dict[str, Any]]] = None,
    clinical_summary: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates an interactive HTML report using Plotly and Jinja2 with resource, anomaly, and variant tracking."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Quality Control Bar Chart
    qc_cols = [c for c in ["adapter_content_flag", "per_base_sequence_quality"] if c in metrics_df.columns]
    if qc_cols:
        qc_long = metrics_df.melt(
            id_vars=["sample_id"],
            value_vars=qc_cols,
            var_name="qc_metric",
            value_name="status",
        )
        color_map = {"PASS": "#10b981", "WARN": "#f59e0b", "FAIL": "#ef4444"}
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
        fig_qc.update_layout(margin=dict(l=40, r=40, t=50, b=40), plot_bgcolor="#fcfcfc")
        qc_chart_html = fig_qc.to_html(full_html=False, include_plotlyjs="cdn")
    else:
        qc_chart_html = "<p>No QC checkpoint columns available.</p>"

    # 2. Alignment Percentage Distribution Chart
    if "mapped_reads" in metrics_df.columns and "total_reads" in metrics_df.columns:
        if len(metrics_df) == 1:
            sample_data = metrics_df.iloc[0]
            unmapped = max(0, sample_data["total_reads"] - sample_data["mapped_reads"])
            fig_align = go.Figure(
                data=[
                    go.Pie(
                        labels=["Mapped Reads", "Unmapped Reads"],
                        values=[sample_data["mapped_reads"], unmapped],
                        hole=0.35,
                        title=f"Alignment: {sample_data['sample_id']}",
                        marker=dict(colors=["#1e3a8a", "#e2e8f0"]),
                    )
                ]
            )
        else:
            cols = len(metrics_df)
            specs = [[{"type": "domain"} for _ in range(cols)]]
            fig_align = make_subplots(
                rows=1,
                cols=cols,
                specs=specs,
                subplot_titles=[str(sid) for sid in metrics_df["sample_id"]],
            )
            for idx, (_, sample_data) in enumerate(metrics_df.iterrows(), start=1):
                unmapped = max(0, sample_data["total_reads"] - sample_data["mapped_reads"])
                fig_align.add_trace(
                    go.Pie(
                        labels=["Mapped Reads", "Unmapped Reads"],
                        values=[sample_data["mapped_reads"], unmapped],
                        hole=0.35,
                        name=str(sample_data["sample_id"]),
                        marker=dict(colors=["#1e3a8a", "#cbd5e1"]),
                    ),
                    row=1,
                    col=idx,
                )

        fig_align.update_layout(
            title_text="Alignment Distribution (Mapped vs. Unmapped Reads)",
            margin=dict(l=40, r=40, t=60, b=40),
        )
        align_chart_html = fig_align.to_html(full_html=False, include_plotlyjs=False)
    else:
        align_chart_html = "<p>No alignment read columns available.</p>"

    # 3. Multi-Sample Resource & Performance Chart
    resource_chart_html = ""
    if "execution_time_sec" in metrics_df.columns or "peak_ram_mb" in metrics_df.columns:
        fig_resource = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=["Execution Time per Sample (seconds)", "Peak RAM Consumption (MB)"],
        )
        if "execution_time_sec" in metrics_df.columns:
            fig_resource.add_trace(
                go.Bar(
                    x=metrics_df["sample_id"],
                    y=metrics_df["execution_time_sec"],
                    name="Runtime (s)",
                    marker_color="#3b82f6",
                ),
                row=1,
                col=1,
            )
        if "peak_ram_mb" in metrics_df.columns:
            fig_resource.add_trace(
                go.Bar(
                    x=metrics_df["sample_id"],
                    y=metrics_df["peak_ram_mb"],
                    name="Peak RAM (MB)",
                    marker_color="#10b981",
                ),
                row=1,
                col=2,
            )
        fig_resource.update_layout(
            height=360,
            margin=dict(l=30, r=30, t=50, b=30),
            showlegend=False,
            plot_bgcolor="#fcfcfc",
        )
        resource_chart_html = fig_resource.to_html(full_html=False, include_plotlyjs=False)

    # 4. Interactive Variant Annotation Table
    variant_table_html = ""
    total_variants_count = 0
    if variants:
        total_variants_count = len(variants)
        var_df = pd.DataFrame(variants)
        v_cols = [
            c
            for c in [
                "sample_id",
                "chrom",
                "pos",
                "gene",
                "hgvsc",
                "hgvsp",
                "consequence",
                "clinvar_status",
                "allele_frequency",
                "read_depth",
            ]
            if c in var_df.columns
        ]
        fig_var_table = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=[f"<b>{c.upper()}</b>" for c in v_cols],
                        fill_color="#5b21b6",
                        font=dict(color="white", size=12),
                        align="left",
                    ),
                    cells=dict(
                        values=[var_df[c] for c in v_cols],
                        fill_color="#faf5ff",
                        font=dict(color="#1e1b4b", size=11),
                        height=28,
                        align="left",
                    ),
                )
            ]
        )
        fig_var_table.update_layout(margin=dict(l=0, r=0, t=10, b=10))
        variant_table_html = fig_var_table.to_html(full_html=False, include_plotlyjs=False)

    # 5. Interactive Metrics Table
    display_cols = [
        c
        for c in [
            "sample_id",
            "execution_mode",
            "mapped_percentage",
            "gc_content_percent",
            "mean_phred_quality",
            "variant_count",
            "status_label",
            "execution_time_sec",
            "peak_ram_mb",
        ]
        if c in metrics_df.columns
    ]
    if not display_cols:
        display_cols = list(metrics_df.columns)

    table_figure = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[f"<b>{col}</b>" for col in display_cols],
                    fill_color="#1e3a8a",
                    font=dict(color="white", size=12),
                    align="left",
                ),
                cells=dict(
                    values=[metrics_df[col] for col in display_cols],
                    fill_color="#f8fafc",
                    font=dict(color="#1e293b", size=11),
                    height=28,
                    align="left",
                ),
            )
        ]
    )
    table_figure.update_layout(margin=dict(l=0, r=0, t=10, b=10))
    table_chart_html = table_figure.to_html(full_html=False, include_plotlyjs=False)

    # Anomaly summary extraction
    anomaly_list: List[Dict[str, Any]] = []
    if "is_anomaly" in metrics_df.columns:
        anomalies_df = metrics_df[metrics_df["is_anomaly"] == True]
        for _, row in anomalies_df.iterrows():
            flags = row.get("anomaly_flags", [])
            if isinstance(flags, str):
                flags = [flags]
            insights = row.get("insights", [])
            if isinstance(insights, str):
                insights = [insights]

            anomaly_list.append({
                "sample_id": row.get("sample_id"),
                "severity": row.get("anomaly_severity", "WARNING"),
                "status_label": row.get("status_label", "Flagged Anomaly"),
                "flags": flags,
                "insights": insights,
            })

    flagged_count = len(anomaly_list)
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
    avg_ram = (
        round(metrics_df["peak_ram_mb"].mean(), 1)
        if "peak_ram_mb" in metrics_df.columns
        else "N/A"
    )

    template = Template(REPORT_HTML_TEMPLATE)
    html_content = template.render(
        project_name=project_name,
        execution_mode=execution_mode.capitalize(),
        generated_date=datetime.date.today().isoformat(),
        total_samples=total_samples,
        flagged_count=flagged_count,
        total_variants=total_variants_count,
        anomaly_list=anomaly_list,
        avg_phred=avg_phred,
        avg_mapping=avg_mapping,
        avg_ram=avg_ram,
        clinical_data=clinical_summary,
        variant_table_html=variant_table_html,
        qc_chart_html=qc_chart_html,
        align_chart_html=align_chart_html,
        resource_chart_html=resource_chart_html,
        table_chart_html=table_chart_html,
    )

    report_path = out_path / "execution_report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Interactive HTML report generated at: {report_path.resolve()}")
    return str(report_path.resolve())
