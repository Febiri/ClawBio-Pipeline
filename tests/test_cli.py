from click.testing import CliRunner
from main import cli
from pathlib import Path


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ClawBio-Pipeline" in result.output
    assert "run-pipeline" in result.output
    assert "validate" in result.output
    assert "generate-samples" in result.output
    assert "serve" in result.output


def test_cli_run_pipeline_simulation():
    runner = CliRunner()
    project_dir = Path(__file__).resolve().parent.parent
    config_path = str(project_dir / "config.yaml")

    result = runner.invoke(cli, ["run-pipeline", "--config", config_path, "--mode", "simulation"])
    assert result.exit_code == 0
    assert "Starting pipeline for project" in result.output
    assert "Interactive HTML report generated" in result.output
    assert "Pipeline execution complete" in result.output


def test_cli_run_pipeline_real(tmp_path):
    runner = CliRunner()
    project_dir = Path(__file__).resolve().parent.parent
    config_path = str(project_dir / "config.yaml")

    result = runner.invoke(
        cli, ["run-pipeline", "--config", config_path, "--mode", "real", "--workers", "2"]
    )
    assert result.exit_code == 0
    assert "Starting pipeline for project" in result.output
    assert "Pipeline execution complete" in result.output


def test_cli_validate():
    runner = CliRunner()
    project_dir = Path(__file__).resolve().parent.parent
    config_path = str(project_dir / "config.yaml")

    result = runner.invoke(cli, ["validate", "--config", config_path])
    assert result.exit_code == 0
    assert "Checking configuration" in result.output


def test_cli_generate_samples(tmp_path):
    runner = CliRunner()
    out_dir = str(tmp_path / "synthetic")
    result = runner.invoke(
        cli, ["generate-samples", "--output-dir", out_dir, "--reads", "25", "--no-update-config"]
    )
    assert result.exit_code == 0
    assert "Dataset generation completed" in result.output
    assert (tmp_path / "synthetic" / "Normal_Control_R1.fastq").exists()
