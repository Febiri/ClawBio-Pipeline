import pytest
from pathlib import Path
import yaml
from src.parser import load_config, get_sample_ids, validate_fastq, validate_samples


def test_load_config_valid(tmp_path):
    config_data = {
        "project_name": "Test Study",
        "reference_genome": "hg38",
        "samples": [{"sample_id": "Sample1", "raw_fastq": "data/sample1.fastq"}],
        "output_dir": "test_results",
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    loaded = load_config(str(cfg_file))
    assert loaded["project_name"] == "Test Study"
    assert loaded["reference_genome"] == "hg38"
    assert len(loaded["samples"]) == 1


def test_load_config_missing():
    with pytest.raises(SystemExit):
        load_config("non_existent_config_file_12345.yaml")


def test_get_sample_ids():
    config = {
        "samples": [
            {"sample_id": "Tumor_1"},
            {"sample_id": "Normal_1"},
            {"sample_id": "Tumor_2"},
        ]
    }
    ids = get_sample_ids(config)
    assert ids == ["Tumor_1", "Normal_1", "Tumor_2"]


def test_get_sample_ids_empty():
    assert get_sample_ids({}) == []
    assert get_sample_ids({"samples": []}) == []


def test_validate_fastq_valid(tmp_path):
    fastq_file = tmp_path / "test.fastq"
    fastq_content = (
        "@SEQ1\n"
        "AGCTAGCTAGCTAGCT\n"
        "+\n"
        "IIIIIIIIIIIIIIII\n"
    )
    fastq_file.write_text(fastq_content, encoding="utf-8")
    assert validate_fastq(fastq_file) is True


def test_validate_fastq_invalid(tmp_path):
    invalid_file = tmp_path / "corrupt.fastq"
    invalid_file.write_text("NOT A FASTQ FILE\nJUST RANDOM TEXT", encoding="utf-8")
    assert validate_fastq(invalid_file) is False


def test_validate_fastq_nonexistent():
    assert validate_fastq(Path("does_not_exist.fastq")) is False


def test_validate_samples(tmp_path):
    fastq_file = tmp_path / "sample.fastq"
    fastq_file.write_text(
        "@SEQ1\nACTG\n+\nIIII\n",
        encoding="utf-8",
    )

    config = {
        "samples": [
            {"sample_id": "ValidSample", "raw_fastq": "sample.fastq"},
            {"sample_id": "MissingSample", "raw_fastq": "missing.fastq"},
        ]
    }

    results = validate_samples(config, base_dir=tmp_path)
    assert results["ValidSample"] is True
    assert results["MissingSample"] is False

