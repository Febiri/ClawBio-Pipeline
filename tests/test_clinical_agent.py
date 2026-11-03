from src.clinical_agent import ClinicalInterpretationAgent


def test_clinical_interpretation_pathogenic():
    agent = ClinicalInterpretationAgent(use_llm_if_available=False)
    mock_variants = [
        {
            "gene": "BRCA1",
            "hgvsc": "c.5266dupC",
            "hgvsp": "p.Gln1756Profs*74",
            "clinvar_status": "Pathogenic",
        },
        {
            "gene": "TP53",
            "hgvsc": "c.818G>A",
            "hgvsp": "p.Arg273His",
            "clinvar_status": "Pathogenic",
        },
    ]

    analysis = agent.analyze_variants(mock_variants)
    assert analysis["total_variants_evaluated"] == 2
    assert analysis["pathogenic_count"] == 2
    assert analysis["actionable_targets_count"] >= 2

    # Check that PARP inhibitors are matched for BRCA1
    brca1_match = next(m for m in analysis["actionable_therapies"] if m["gene"] == "BRCA1")
    assert "PARP Inhibitors" in brca1_match["therapy_class"]
    assert any("Olaparib" in drug for drug in brca1_match["recommended_drugs"])
    assert "Level 1A" in brca1_match["evidence_level"]
    assert "NCT" in brca1_match["matched_trial"]


def test_clinical_interpretation_benign_only():
    agent = ClinicalInterpretationAgent(use_llm_if_available=False)
    benign_variants = [
        {
            "gene": "TP53",
            "hgvsc": "c.215C>G",
            "hgvsp": "p.Pro72Arg",
            "clinvar_status": "Benign",
        }
    ]

    analysis = agent.analyze_variants(benign_variants)
    assert analysis["total_variants_evaluated"] == 1
    assert analysis["pathogenic_count"] == 0
    assert analysis["actionable_targets_count"] == 0
    assert "No high-penetrance actionable" in analysis["clinical_narrative"]
