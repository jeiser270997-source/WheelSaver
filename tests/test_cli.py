from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_cli_version_or_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "WheelSaver" in result.stdout or "Usage" in result.stdout


def test_cli_stats():
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0


def test_cli_search_no_args():
    result = runner.invoke(app, ["search"])
    # Debe requerir keyword o devolver ayuda/error de argumentos
    assert result.exit_code != 0 or "Usage" in result.stdout
