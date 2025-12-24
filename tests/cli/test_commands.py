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
            'personas',
            [
                {
                    'name': 'test_persona',
                    'description': 'A test persona',
                    'uuid': '1234',
                    'files': [],
                }
            ],
        )
        mock_vector_db_class.return_value = vector_db
        yield vector_db


def test_list_templates_personas(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Act
    result = runner.invoke(app, ['personas', 'list'])

    # Assert
    assert result.exit_code == 0
    assert 'test_persona' in result.stdout


def test_list_templates_empty(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Arrange
    mock_vector_db.drop_all_tables()
    mock_vector_db.create_persona_tables()

    # Act
    result = runner.invoke(app, ['personas', 'list'])

    # Assert
    assert result.exit_code == 0


def test_copy_template(
    runner: CliRunner, mock_storage: MagicMock, tmp_path: Path, mock_vector_db: VectorDatabase
) -> None:
    # Arrange
    template_path = tmp_path / 'PERSONA.md'
    with open(template_path, 'w') as f:
        f.write('---\nname: new_persona\ndescription: A new persona\n---\n')

    entry = IndexEntry(
        name='new_persona',
        description='A new persona',
        uuid='5678',
        type='persona',
    )
    mock_storage._metadata = [('upsert', entry)]

    # Act
    result = runner.invoke(
        app,
        ['personas', 'register', str(template_path)],
    )

    # Assert
    assert result.exit_code == 0
    mock_storage.save.assert_called()

    assert mock_vector_db.exists('personas', 'new_persona')


def test_remove_template(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Act
    result = runner.invoke(app, ['personas', 'remove', 'test_persona'])

    # Assert
    assert result.exit_code == 0
    assert 'Template "test_persona" has been removed' in result.stdout

    assert not mock_vector_db.exists('personas', 'test_persona')


def test_remove_template_not_found(
    runner: CliRunner, mock_storage: MagicMock, mock_vector_db: VectorDatabase
) -> None:
    # Act
    result = runner.invoke(app, ['personas', 'remove', 'non_existent_persona'])

    # Assert
    assert result.exit_code != 0
    assert 'Persona "non_existent_persona" does not exist' in result.stdout
