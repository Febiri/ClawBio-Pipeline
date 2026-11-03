from typing import Dict, Any, List, Optional


DEFAULT_QC_THRESHOLDS = {
    "min_mapped_percentage": 95.0,
    "reference_gc_percent": 41.0,  # Human genome hg38 baseline (~41%)
    "max_gc_deviation": 10.0,      # Flag if GC < 31% or > 51%
    "min_phred_quality": 30.0,     # Standard Q30 threshold
    "max_duplication_rate": 8.0,   # Flag if duplication > 8%
}


class AnomalyDetector:
    """Smart Insight Engine for biological variant and sequencing anomaly detection."""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = dict(DEFAULT_QC_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def evaluate_sample(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates sample metrics against biological QC thresholds.

        Args:
            metrics: Dictionary of sample QC and alignment statistics.

        Returns:
            Dict containing anomaly status, severity level, flags, and biological insights.
        """
        flags: List[str] = []
        insights: List[str] = []
        severities: List[str] = []

        # 1. Alignment / Mapped Reads Check
        mapped_pct = metrics.get("mapped_percentage")
        if mapped_pct is not None:
            min_mapped = self.thresholds["min_mapped_percentage"]
            if mapped_pct < min_mapped:
                flags.append(f"Low Mapping Rate: {mapped_pct:.1f}% (< {min_mapped:.1f}%)")
                if mapped_pct < 90.0:
                    severities.append("CRITICAL")
                    insights.append(
                        "Severe mapping deficit (<90%). Possible reference genome mismatch, high contamination, or library degradation."
                    )
                else:
                    severities.append("WARNING")
                    insights.append(
                        "Sub-optimal alignment rate. Review adapter trimming parameters or check for unmapped viral/bacterial reads."
                    )

        # 2. GC Content Deviation Check
        gc_content = metrics.get("gc_content_percent")
        if gc_content is not None:
            ref_gc = self.thresholds["reference_gc_percent"]
            max_dev = self.thresholds["max_gc_deviation"]
            gc_dev = abs(gc_content - ref_gc)
            if gc_dev > max_dev:
                flags.append(
                    f"GC Bias Detected: {gc_content:.1f}% (deviation {gc_dev:+.1f}% from ref {ref_gc:.1f}%)"
                )
                severities.append("WARNING")
                insights.append(
                    f"GC content ({gc_content:.1f}%) significantly deviates from reference baseline ({ref_gc:.1f}%). "
                    "Indicates potential PCR amplification bias, primer-dimer enrichment, or microbial contamination."
                )

        # 3. Phred Quality Score Check
        phred = metrics.get("mean_phred_quality")
        if phred is not None:
            min_phred = self.thresholds["min_phred_quality"]
            if phred < min_phred:
                flags.append(f"Sub-optimal Quality Score: Q{phred:.1f} (< Q{min_phred:.1f})")
                if phred < 25.0:
                    severities.append("CRITICAL")
                    insights.append(
                        "Critical base quality failure (Q < 25). High probability of sequencing chemistry failure or optical sensor drift."
                    )
                else:
                    severities.append("WARNING")
                    insights.append(
                        "Moderate base call quality drop. Downstream variant calling may suffer from false positive SNP calls."
                    )

        # 4. Adapter Contamination Check
        adapter_flag = metrics.get("adapter_content_flag")
        if adapter_flag in ["WARN", "FAIL"]:
            flags.append(f"Adapter Contamination Flagged ({adapter_flag})")
            severities.append("WARNING")
            insights.append(
                "Excess adapter sequences identified. Recommend stringent adapter clipping (e.g. Trimmomatic or fastp) prior to alignment."
            )

        # 5. Duplication Rate Check
        dup_rate = metrics.get("duplication_rate_percent")
        if dup_rate is not None:
            max_dup = self.thresholds["max_duplication_rate"]
            if dup_rate > max_dup:
                flags.append(f"Elevated Duplication: {dup_rate:.1f}% (> {max_dup:.1f}%)")
                severities.append("WARNING")
                insights.append(
                    "High optical/PCR duplicate rate. Indicates low initial DNA input or over-amplification in library prep."
                )

        # Determine overall sample severity
        if "CRITICAL" in severities:
            overall_severity = "CRITICAL"
            is_anomaly = True
            status_label = "Low-Quality Sample / Potential Sequencing Artifact"
        elif "WARNING" in severities:
            overall_severity = "WARNING"
            is_anomaly = True
            status_label = "Quality Warning / Review Required"
        else:
            overall_severity = "PASS"
            is_anomaly = False
            status_label = "Optimal Sequencing Quality"

        return {
            "is_anomaly": is_anomaly,
            "anomaly_severity": overall_severity,
            "status_label": status_label,
            "anomaly_flags": flags,
            "flags_summary": "; ".join(flags) if flags else "None",
            "insights": insights,
        }

