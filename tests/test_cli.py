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


def test_cli_run_pipeline(tmp_path):
    runner = CliRunner()
    # Run with default config (pointing to existing config.yaml in workspace)
    project_dir = Path(__file__).resolve().parent.parent
    config_path = str(project_dir / "config.yaml")

    result = runner.invoke(cli, ["run-pipeline", "--config", config_path])
    assert result.exit_code == 0
    assert "Starting pipeline for project" in result.output
    assert "Interactive HTML report generated" in result.output
    assert "Pipeline execution complete" in result.output


def test_cli_validate():
    runner = CliRunner()
    project_dir = Path(__file__).resolve().parent.parent
    config_path = str(project_dir / "config.yaml")

    result = runner.invoke(cli, ["validate", "--config", config_path])
    assert result.exit_code == 0
    assert "Checking configuration" in result.output

