import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from persona.storage import VectorDatabase
from persona.cli import app


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
        with patch('persona.cli.commands.VectorDatabase') as mock_vector_db:
            mock_vector_db.return_value = MagicMock()
            mock_local_storage_load.return_value = MagicMock()
            # Act
            result = runner.invoke(
                app,
                [
                    '--config',
                    str(mock_config_file),
                    '--set',
                    'index=index2',
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


def test_reindex(
    runner: CliRunner, mock_config_file: Path, mock_home: Path, vector_db: VectorDatabase
) -> None:
    # Arrange
    (mock_home / 'personas' / 'test_persona').mkdir(parents=True)
    (mock_home / 'skills' / 'test_skill').mkdir(parents=True)
    with open(mock_home / 'personas' / 'test_persona' / 'PERSONA.md', 'w') as f:
        f.write('---\nname: test_persona\ndescription: A test persona\n---\n')
    with open(mock_home / 'skills' / 'test_skill' / 'SKILL.md', 'w') as f:
        f.write('---\nname: test_skill\ndescription: A test skill\n---\n')

    # Act
    with patch('persona.cli.VectorDatabase', return_value=vector_db):
        result = runner.invoke(app, ['--config', str(mock_config_file), 'reindex'])

    # Assert
    assert result.exit_code == 0

    personas = vector_db.get_or_create_table('personas')
    skills = vector_db.get_or_create_table('skills')

    assert personas.count_rows() == 1
    assert skills.count_rows() == 1


def test_reindex_no_files(
    runner: CliRunner, mock_config_file: Path, vector_db: VectorDatabase
) -> None:
    # Arrange
    # Act
    with patch('persona.cli.VectorDatabase', return_value=vector_db):
        result = runner.invoke(app, ['--config', str(mock_config_file), 'reindex'])

    # Assert
    assert result.exit_code == 0

    assert vector_db.get_or_create_table('personas').count_rows() == 0
    assert vector_db.get_or_create_table('skills').count_rows() == 0


def test_init(
    runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch, mock_config_file: Path
) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_STORAGE_TYPE', 'local')
    config_path = mock_home.parent / '.persona.config.yaml'

    # Act
    result = runner.invoke(app, ['--config', str(config_path), 'init'])

    # Assert
    assert result.exit_code == 0
    assert config_path.exists()
    assert (mock_home / 'personas').exists()
    assert (mock_home / 'skills').exists()
    assert (mock_home / 'index').exists()
    assert (mock_home / 'index' / 'personas.lance').exists()
    assert (mock_home / 'index' / 'skills.lance').exists()


def test_init_already_exists(runner: CliRunner, mock_config_file: Path) -> None:
    # Arrange
    # Act
    result = runner.invoke(app, ['--config', str(mock_config_file), 'init'])

    # Assert
    assert result.exit_code == 0
