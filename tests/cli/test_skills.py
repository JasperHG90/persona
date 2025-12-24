from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from persona.cli import app
from persona.storage import IndexEntry, VectorDatabase


@pytest.fixture
def mock_storage(tmp_path: Path):
    with patch('persona.cli.commands.get_storage_backend') as mock_get_storage_backend:
        mock = MagicMock()
        mock_get_storage_backend.return_value = mock
        mock_get_storage_backend.config.index_path = tmp_path / 'index'
        yield mock


@pytest.fixture
def mock_vector_db(
    vector_db: VectorDatabase,
):  ## NB: from top-level conftest - function-scoped fixture
    with patch('persona.cli.commands.VectorDatabase') as mock_vector_db_class:
        vector_db.update_table(
            'skills',
            [
                {
                    'name': 'test_skill',
                    'description': 'A test skill',
                    'uuid': '1234',
                    'files': [],
                }
            ],
        )
        mock_vector_db_class.return_value = vector_db
        yield vector_db


def test_register_skill(
    runner: CliRunner, mock_storage: MagicMock, tmp_path: Path, mock_vector_db: VectorDatabase
) -> None:
    # Arrange
    template_path = tmp_path / 'SKILL.md'
    with open(template_path, 'w') as f:
        f.write('---\nname: new_skill\ndescription: A new skill\n---\n')

    entry = IndexEntry(
        name='new_skill',
        description='A new skill',
        uuid='5678',
        type='skill',
    )
    mock_storage._metadata = [('upsert', entry)]

    # Act
    result = runner.invoke(
        app,
        ['skills', 'register', str(template_path)],
    )

    # Assert
    assert result.exit_code == 0
    mock_storage.save.assert_called()

    assert mock_vector_db.exists('skills', 'new_skill')


def test_register_skill_already_exists(
    runner: CliRunner, mock_storage: MagicMock, tmp_path: Path, mock_vector_db: VectorDatabase
) -> None:
    # Arrange
    template_path = tmp_path / 'SKILL.md'
    with open(template_path, 'w') as f:
        f.write('---\nname: test_skill\ndescription: A test skill\n---\n')

    # Act
    result = runner.invoke(
        app,
        ['skills', 'register', str(template_path)],
    )

    # Assert
    assert result.exit_code == 0


def test_remove_skill(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Act
    result = runner.invoke(app, ['skills', 'remove', 'test_skill'])

    # Assert
    assert result.exit_code == 0
    assert 'Template "test_skill" has been removed' in result.stdout

    assert not mock_vector_db.exists('skills', 'test_skill')


def test_remove_skill_not_found(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Act
    result = runner.invoke(app, ['skills', 'remove', 'non_existent_skill'])

    # Assert
    assert result.exit_code != 0
    assert 'Skill "non_existent_skill" does not exist' in result.stdout


def test_list_skills(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Act
    result = runner.invoke(app, ['skills', 'list'])

    # Assert
    assert result.exit_code == 0
    assert 'test_skill' in result.stdout


def test_list_skills_empty(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Arrange
    mock_vector_db.drop_all_tables()
    mock_vector_db.create_persona_tables()

    # Act
    result = runner.invoke(app, ['skills', 'list'])

    # Assert
    assert result.exit_code == 0
