from pathlib import Path
from src.variant_engine import call_and_annotate_variants, write_vcf_file, KNOWN_CLINICAL_VARIANTS


def test_call_and_annotate_tumor_variants(tmp_path):
    sample_id = "Tumor_Sample_01"
    vcf_dir = tmp_path / "variants"

    variants = call_and_annotate_variants(
        sample_id=sample_id,
        mode="simulation",
        output_dir=vcf_dir,
    )

    assert len(variants) >= 2
    genes = [v["gene"] for v in variants]
    assert "TP53" in genes
    assert "BRCA1" in genes

    tp53_var = next(v for v in variants if v["gene"] == "TP53")
    assert tp53_var["clinvar_status"] == "Pathogenic"
    assert "p.Arg273His" in tp53_var["hgvsp"]
    assert tp53_var["allele_frequency"] > 0.2

    # Check generated VCF file
    vcf_file = vcf_dir / f"{sample_id}.vcf"
    assert vcf_file.exists()
    content = vcf_file.read_text(encoding="utf-8")
    assert "##fileformat=VCFv4.2" in content
    assert "GENE=TP53" in content
    assert "CLNSIG=Pathogenic" in content


def test_call_and_annotate_normal_variants(tmp_path):
    sample_id = "Normal_Control_01"
    vcf_dir = tmp_path / "variants"

    variants = call_and_annotate_variants(
        sample_id=sample_id,
        mode="simulation",
        output_dir=vcf_dir,
    )

    assert len(variants) >= 1
    # Normal control should only have benign polymorphisms
    for v in variants:
        assert v["clinvar_status"] == "Benign"


def test_write_vcf_file(tmp_path):
    output_vcf = tmp_path / "test.vcf"
    sample_id = "Sample_VCF_Test"
    mock_variants = [
        {
            "chrom": "chr17",
            "pos": 7673802,
            "ref": "C",
            "alt": "T",
            "gene": "TP53",
            "hgvsc": "c.818G>A",
            "hgvsp": "p.Arg273His",
            "consequence": "missense_variant",
            "clinvar_status": "Pathogenic",
            "acmg_classification": "PS1",
            "cancer_type": "Ovarian_Cancer",
            "read_depth": 100,
            "allele_frequency": 0.45,
            "genotype": "0/1",
            "filter": "PASS",
            "qual": 99.0,
        }
    ]

    res = write_vcf_file(mock_variants, output_vcf, sample_id)
    assert res.exists()
    text = res.read_text(encoding="utf-8")
    assert "#CHROM\tPOS\tID\tREF\tALT" in text
    assert "Sample_VCF_Test" in text
