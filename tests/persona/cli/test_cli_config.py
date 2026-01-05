from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from persona.cli import app


def test_config_cache_dir(runner: CliRunner) -> None:
    # Arrange
    with patch('persona.cli.config.user_cache_dir') as mock_cache:
        mock_cache.return_value = '/mock/cache'

        # Act
        result = runner.invoke(app, ['config', 'cache_dir'])

        # Assert
        assert result.exit_code == 0
        assert '/mock/cache' in result.stdout


def test_config_data_dir(runner: CliRunner) -> None:
    # Arrange
    with patch('persona.cli.config.user_data_dir') as mock_data:
        mock_data.return_value = '/mock/data'

        # Act
        result = runner.invoke(app, ['config', 'data_dir'])

        # Assert
        assert result.exit_code == 0
        assert '/mock/data' in result.stdout


def test_config_root_dir(runner: CliRunner) -> None:
    # Arrange
    mock_config = MagicMock()
    mock_config.root_normalized = '/mock/root'

    # We mock parse_persona_config to return our mock config
    # We also mock Path.exists to False to avoid file operations in the main callback
    with patch('persona.cli.parse_persona_config', return_value=mock_config):
        with patch('pathlib.Path.exists', return_value=False):
            # Act
            result = runner.invoke(app, ['config', 'root_dir'])

            # Assert
            assert result.exit_code == 0
            assert '/mock/root' in result.stdout
