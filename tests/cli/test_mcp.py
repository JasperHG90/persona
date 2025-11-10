
from unittest.mock import patch

from typer.testing import CliRunner

from persona.cli import app


def test_start_server(runner: CliRunner) -> None:
    # Arrange
    with patch("persona.cli.mcp.entrypoint") as mock_entrypoint:
        # Act
        result = runner.invoke(app, ["mcp", "start"])

        # Assert
        assert result.exit_code == 0
        mock_entrypoint.assert_called_once()


def test_start_server_no_deps(runner: CliRunner) -> None:
    # Arrange
    with patch("persona.cli.mcp._has_mcp_deps", False):
        # Act
        result = runner.invoke(app, ["mcp", "start"])

        # Assert
        assert result.exit_code == 1
        assert "MCP dependencies are not installed" in result.stdout
