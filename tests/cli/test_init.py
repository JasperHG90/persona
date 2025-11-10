import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from persona.cli import app
from persona.storage import Index, SubIndex


def test_main_debug(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), '--debug', 'personas', 'list'])

    # Assert
    assert result.exit_code == 0
    assert logging.getLogger('persona').level == logging.DEBUG


def test_main_config_path(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'personas', 'list'])

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
    result = runner.invoke(app, ['personas', 'list'])

    # Assert
    assert result.exit_code == 0


def test_main_set_vars(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    with patch('persona.storage.local.LocalStorageBackend.load') as mock_local_storage_load:
        mock_local_storage_load.return_value = Index(
            personas=SubIndex(root={}), skills=SubIndex(root={})
        ).model_dump_json()
        # Act
        result = runner.invoke(
            app,
            [
                '--config',
                str(mock_config_file),
                '--set',
                'root=/new/root',
                'personas',
                'list',
            ],
        )

        # Assert
        assert result.exit_code == 0


def test_main_set_vars_invalid(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Act
    result = runner.invoke(
        app,
        [
            '--config',
            str(mock_config_file),
            '--set',
            'root',
            'personas',
            'list',
        ],
    )

    # Assert
    assert result.exit_code != 0
    assert 'Invalid format for --set option' in result.stderr


def test_main_no_config_file(
    runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_STORAGE_TYPE', 'local')
    # Act
    result = runner.invoke(app, ['--config', str(mock_home / 'nonexistent.yaml'), 'init'])

    # Assert
    assert result.exit_code == 0


def test_main_malformed_config(runner: CliRunner, mock_home: Path) -> None:
    # Arrange
    config_file = mock_home / 'malformed.yaml'
    with open(config_file, 'w') as f:
        f.write(':')

    # Act
    result = runner.invoke(app, ['--config', str(config_file), 'personas', 'list'])

    # Assert
    assert result.exit_code != 0
    assert 'Error loading configuration' in result.stdout


def test_reindex(runner: CliRunner, mock_config_file: Path, mock_home: Path) -> None:
    # Arrange
    (mock_home / 'personas' / 'test_persona').mkdir(parents=True)
    (mock_home / 'skills' / 'test_skill').mkdir(parents=True)
    with open(mock_home / 'personas' / 'test_persona' / 'PERSONA.md', 'w') as f:
        f.write('---\nname: test_persona\ndescription: A test persona\n---\n')
    with open(mock_home / 'skills' / 'test_skill' / 'SKILL.md', 'w') as f:
        f.write('---\nname: test_skill\ndescription: A test skill\n---\n')

    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'reindex'])

    # Assert
    assert result.exit_code == 0
    with open(mock_home / 'index.json', 'r') as f:
        index = json.load(f)
    assert 'test_persona' in index['personas']
    assert 'test_skill' in index['skills']


def test_reindex_no_files(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'reindex'])

    # Assert
    assert result.exit_code == 0


def test_init(runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_STORAGE_TYPE', 'local')
    config_path = mock_home / '.persona.config.yaml'

    # Act
    result = runner.invoke(app, ['--config', str(config_path), 'init'])

    # Assert
    assert result.exit_code == 0
    assert config_path.exists()
    assert (mock_home / '.persona' / 'personas').exists()
    assert (mock_home / '.persona' / 'skills').exists()
    assert (mock_home / '.persona' / 'index.json').exists()


def test_init_already_exists(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'init'])

    # Assert
    assert result.exit_code == 0
