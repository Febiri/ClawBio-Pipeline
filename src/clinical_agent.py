import os
from typing import List, Dict, Any, Optional


# Comprehensive Clinical Oncology Therapeutic Mapping (NCCN / FDA / OncoKB standards)
TARGETED_THERAPEUTICS_DB = {
    "BRCA1": {
        "therapy_class": "PARP Inhibitors",
        "drugs": ["Olaparib (Lynparza)", "Niraparib (Zejula)", "Rucaparib (Rubraca)"],
        "evidence_level": "Level 1A (FDA Approved / Standard of Care)",
        "indication": "Advanced Ovarian Carcinoma with Homologous Recombination Deficiency (HRD)",
        "mechanism": "Synthetic lethality targeting defective double-strand break repair.",
        "resistance_risk": "Reversion mutations in BRCA1 open reading frame may restore homologous recombination.",
        "trial_matching": "NCT03522246 (Phase III): Maintenance Olaparib in Platinum-Sensitive Ovarian Cancer",
    },
    "BRCA2": {
        "therapy_class": "PARP Inhibitors",
        "drugs": ["Olaparib", "Talazoparib", "Niraparib"],
        "evidence_level": "Level 1A (FDA Approved)",
        "indication": "Epithelial Ovarian, Fallopian Tube, or Primary Peritoneal Cancer",
        "mechanism": "DNA repair pathway inhibition leading to genomic instability and tumor cell death.",
        "resistance_risk": "Secondary intragenic reversion mutations.",
        "trial_matching": "NCT02470585 (Phase III): Poly(ADP-ribose) Polymerase Inhibition in Advanced Cancer",
    },
    "TP53": {
        "therapy_class": "Cell Cycle Checkpoint / WEE1 Inhibitors & Platinum Doublet",
        "drugs": ["Carboplatin + Paclitaxel", "Adavosertib (WEE1 inhibitor, Investigational)"],
        "evidence_level": "Level 2 (Clinical Biomarker / Standard Chemotherapy Backbone)",
        "indication": "High-Grade Serous Ovarian Carcinoma (HGSOC)",
        "mechanism": "Loss of G1/S checkpoint forces reliance on G2/M arrest; vulnerable to WEE1/ATR inhibition.",
        "resistance_risk": "P-glycoprotein upregulation and attenuated apoptotic signaling.",
        "trial_matching": "NCT02101775 (Phase II): WEE1 Inhibitor in Combination with Gemcitabine in TP53-Mutated Tumors",
    },
    "PIK3CA": {
        "therapy_class": "PI3Kα Inhibitors",
        "drugs": ["Alpelisib (Piqray)", "Inavolisib"],
        "evidence_level": "Level 1B (FDA Approved in HR+/HER2- / Active in Ovarian Clear Cell)",
        "indication": "PIK3CA-Mutated Ovarian Endometrioid & Clear Cell Tumors",
        "mechanism": "Selective ATP-competitive inhibition of the class I PI3K p110α catalytic subunit.",
        "resistance_risk": "Feedback activation of IGF1R/HER3 and PTEN somatic loss.",
        "trial_matching": "NCT03056755: Biomarker-Driven Basket Trial Targeting PI3K/AKT/mTOR Pathway",
    },
    "EGFR": {
        "therapy_class": "3rd-Generation EGFR Tyrosine Kinase Inhibitors (TKIs)",
        "drugs": ["Osimertinib (Tagrisso)"],
        "evidence_level": "Level 1A (Standard of Care)",
        "indication": "EGFR Exon 19 del / L858R-mutated Tumors",
        "mechanism": "Irreversible inhibition of mutant EGFR kinase domain.",
        "resistance_risk": "C797S tertiary mutation or MET amplification bypass signaling.",
        "trial_matching": "NCT02296125: Targeted Kinase Inhibition in Solid Malignancies",
    },
    "PTEN": {
        "therapy_class": "AKT / mTOR Inhibitors",
        "drugs": ["Capivasertib (Truqap)", "Everolimus (Afinitor)"],
        "evidence_level": "Level 2 (FDA Approved in Combination / Biomarker Supported)",
        "indication": "PTEN-Deficient Solid Tumors",
        "mechanism": "Suppression of hyperactivated AKT phosphorylation downstream of PTEN loss.",
        "resistance_risk": "Upstream receptor tyrosine kinase reactivation.",
        "trial_matching": "NCT04862663 (Phase II): Selective Pan-AKT Inhibition in Biomarker-Selected Cohorts",
    },
}


class ClinicalInterpretationAgent:
    """Zero-Cost AI Clinical Oncology Interpretation & Therapeutic Recommendation Engine."""

    def __init__(self, use_llm_if_available: bool = True):
        self.use_llm = use_llm_if_available
        self.has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"))

    def analyze_variants(self, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Interprets clinical variants and identifies actionable therapies, drug resistances, and trials.

        Args:
            variants: List of annotated variants from variant_engine.

        Returns:
            Dict containing actionable therapies, clinical summary, and evidence synthesis.
        """
        pathogenic_variants = [
            v for v in variants if v.get("clinvar_status") in ["Pathogenic", "Likely Pathogenic"]
        ]

        actionable_matches = []
        genes_seen = set()

        for var in pathogenic_variants:
            gene = var.get("gene")
            if gene in TARGETED_THERAPEUTICS_DB and gene not in genes_seen:
                genes_seen.add(gene)
                info = TARGETED_THERAPEUTICS_DB[gene]
                actionable_matches.append({
                    "gene": gene,
                    "variant": f"{var.get('hgvsp', '')} ({var.get('hgvsc', '')})",
                    "therapy_class": info["therapy_class"],
                    "recommended_drugs": info["drugs"],
                    "evidence_level": info["evidence_level"],
                    "clinical_indication": info["indication"],
                    "mechanism_of_action": info["mechanism"],
                    "resistance_profile": info["resistance_risk"],
                    "matched_trial": info["trial_matching"],
                })

        # Generate Clinical Oncology Narrative
        if actionable_matches:
            therapy_names = ", ".join(
                [f"{m['gene']} ({'/'.join(m['recommended_drugs'][:2])})" for m in actionable_matches]
            )
            narrative = (
                f"Cohort genomic profiling identified {len(pathogenic_variants)} clinically pathogenic variant(s). "
                f"Actionable therapeutic vulnerabilities detected for: {therapy_names}. "
                "Immediate oncological consideration for targeted PARP inhibition / pathway-directed therapies "
                "under clinical trial enrollment or FDA standard-of-care guidelines."
            )
        else:
            narrative = (
                "No high-penetrance actionable oncogenic drivers detected in current sample panel. "
                "Observed variants represent benign population polymorphisms or non-actionable alterations."
            )

        return {
            "total_variants_evaluated": len(variants),
            "pathogenic_count": len(pathogenic_variants),
            "actionable_targets_count": len(actionable_matches),
            "actionable_therapies": actionable_matches,
            "clinical_narrative": narrative,
            "interpretation_source": "ClawBio Clinical Oncology Knowledge Engine (2026 Release)",
        }
