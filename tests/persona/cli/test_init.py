import logging
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from persona.cli import app


def test_main_debug(runner: CliRunner, mock_config_file: Path) -> None:
    # Act
    # We use 'roles' command just as a placeholder to trigger the callback
    result = runner.invoke(app, ['--config', str(mock_config_file), '--debug', 'roles', 'list'])

    # Assert
    assert result.exit_code == 0
    assert logging.getLogger('persona').level == logging.DEBUG


def test_main_config_path(runner: CliRunner, mock_config_file: Path) -> None:
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'roles', 'list'])

    # Assert
    assert result.exit_code == 0


def test_main_config_path_env_var(
    runner: CliRunner,
    mock_config_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_CONFIG_PATH', str(mock_config_file))

    # Act
    result = runner.invoke(app, ['roles', 'list'])

    # Assert
    assert result.exit_code == 0


def test_main_set_vars(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Mocking get_meta_store_backend to avoid database connection
    with patch('persona.cli.commands.get_meta_store_backend') as mock_meta:
        mock_meta.return_value.open.return_value.__enter__.return_value = MagicMock()
        # Act
        result = runner.invoke(
            app,
            [
                '--config',
                str(mock_config_file),
                '--set',
                'root=/tmp/other_root',
                'roles',
                'list',
            ],
        )

        # Assert
        assert result.exit_code == 0


def test_main_set_vars_invalid(runner: CliRunner, mock_config_file: Path) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            '--config',
            str(mock_config_file),
            '--set',
            'root',
            'roles',
            'list',
        ],
    )

    # Assert
    assert result.exit_code != 0
    # Strip ANSI codes to handle CI/Rich formatting differences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    stderr_clean = ansi_escape.sub('', result.stderr)
    assert 'Invalid format for --set option' in stderr_clean


def test_main_no_config_file(
    runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_STORAGE_TYPE', 'local')
    # Act
    # Provide minimal required config via --set to avoid KeyError in parse_persona_config
    result = runner.invoke(
        app,
        [
            '--config',
            str(mock_home / 'nonexistent.yaml'),
            '--set',
            'file_store.type=local',
            '--set',
            'meta_store.type=duckdb',
            'init',
        ],
    )

    # Assert
    assert result.exit_code == 0


def test_main_malformed_config(runner: CliRunner, mock_home: Path) -> None:
    # Arrange
    config_file = mock_home / 'malformed.yaml'
    with open(config_file, 'w') as f:
        f.write(':')

    # Act
    result = runner.invoke(app, ['--config', str(config_file), 'roles', 'list'])

    # Assert
    assert result.exit_code != 0
    assert 'Error loading configuration' in result.stdout


def test_init(runner: CliRunner, mock_home: Path, mock_config_file: Path) -> None:
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'init'])

    # Assert
    assert result.exit_code == 0
    assert mock_config_file.exists()
    assert (mock_home / 'roles').exists()
    assert (mock_home / 'skills').exists()
    # Metastore index folder
    assert (mock_home / 'index').exists()


def test_init_already_exists(runner: CliRunner, mock_config_file: Path) -> None:
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'init'])

    # Assert
    assert result.exit_code == 0
