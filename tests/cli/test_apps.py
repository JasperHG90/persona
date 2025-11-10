from typer.testing import CliRunner

from persona.cli.personas import app as personas_app
from persona.cli.skills import app as skills_app


def test_personas_app(runner: CliRunner) -> None:
    # Arrange
    # Act
    result = runner.invoke(personas_app, ['--help'])

    # Assert
    assert result.exit_code == 0
    assert 'Manage LLM personas' in result.stdout


def test_skills_app(runner: CliRunner) -> None:
    # Arrange
    # Act
    result = runner.invoke(skills_app, ['--help'])

    # Assert
    assert result.exit_code == 0
    assert 'Manage LLM skills' in result.stdout
