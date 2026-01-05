from unittest.mock import patch
import sys
from typer.testing import CliRunner
from persona.cli import app


def test_start_server(runner: CliRunner) -> None:
    # Arrange
    # We patch the target function where it lives: persona.mcp.server.entrypoint
    with patch('persona.mcp.server.entrypoint') as mock_entrypoint:
        # Act
        result = runner.invoke(app, ['mcp', 'start'])

        # Assert
        assert result.exit_code == 0
        mock_entrypoint.assert_called_once()


def test_start_server_no_deps(runner: CliRunner) -> None:
    # Arrange
    # We simulate missing dependencies by making the import fail
    with patch.dict(sys.modules, {'persona.mcp.server': None}):
        # Act
        result = runner.invoke(app, ['mcp', 'start'])

        # Assert
        assert result.exit_code == 1
        assert 'MCP dependencies are not installed' in result.stdout
