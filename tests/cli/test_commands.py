from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from persona.cli import app
from persona.storage import IndexEntry


@pytest.fixture
def mock_storage():
    with patch('persona.cli.commands.get_storage_backend') as mock_get_storage_backend:
        mock = MagicMock()
        mock_get_storage_backend.return_value = mock
        mock.load.return_value = (
            Index(personas=SubIndex(root={}), skills=SubIndex(root={}))
            .model_dump_json()
            .encode('utf-8')
        )
        yield mock


def test_list_templates_personas(runner: CliRunner, mock_storage: MagicMock) -> None:
    # Arrange
    index = Index(
        personas=SubIndex(
            root={
                'test_persona': IndexEntry(
                    name='test_persona',
                    description='A test persona',
                    uuid='1234',
                )
            }
        ),
        skills=SubIndex(root={}),
    )
    mock_storage.load.return_value = index.model_dump_json()

    # Act
    result = runner.invoke(app, ['personas', 'list'])

    # Assert
    assert result.exit_code == 0
    assert 'test_persona' in result.stdout


def test_list_templates_skills(runner: CliRunner, mock_storage: MagicMock) -> None:
    # Arrange
    index = Index(
        personas=SubIndex(root={}),
        skills=SubIndex(
            root={
                'test_skill': IndexEntry(
                    name='test_skill',
                    description='A test skill',
                    uuid='5678',
                )
            }
        ),
    )
    mock_storage.load.return_value = index.model_dump_json()

    # Act
    result = runner.invoke(app, ['skills', 'list'])

    # Assert
    assert result.exit_code == 0
    assert 'test_skill' in result.stdout


def test_list_templates_empty(runner: CliRunner, mock_storage: MagicMock) -> None:
    # Arrange
    index = Index(personas=SubIndex(root={}), skills=SubIndex(root={}))
    mock_storage.load.return_value = index.model_dump_json()

    # Act
    result = runner.invoke(app, ['personas', 'list'])

    # Assert
    assert result.exit_code == 0


def test_copy_template(runner: CliRunner, mock_storage: MagicMock, tmp_path: Path) -> None:
    # Arrange
    template_path = tmp_path / 'PERSONA.md'
    with open(template_path, 'w') as f:
        f.write('---\nname: new_persona\ndescription: A new persona\n---\n')

    # Act
    result = runner.invoke(
        app,
        ['personas', 'register', str(template_path)],
    )

    # Assert
    assert result.exit_code == 0
    mock_storage.save.assert_called()


def test_remove_template(runner: CliRunner, mock_storage: MagicMock) -> None:
    # Arrange
    index = Index(
        personas=SubIndex(
            root={
                'test_persona': IndexEntry(
                    name='test_persona',
                    description='A test persona',
                    uuid='1234',
                )
            }
        ),
        skills=SubIndex(root={}),
    )
    mock_storage.load.return_value = index.model_dump_json()

    # Act
    result = runner.invoke(app, ['personas', 'remove', 'test_persona'])

    # Assert
    assert result.exit_code == 0
    assert 'Template "test_persona" has been removed' in result.stdout


def test_remove_template_not_found(runner: CliRunner, mock_storage: MagicMock) -> None:
    # Arrange
    index = Index(personas=SubIndex(root={}), skills=SubIndex(root={}))
    mock_storage.load.return_value = index.model_dump_json()

    # Act
    result = runner.invoke(app, ['personas', 'remove', 'non_existent_persona'])

    # Assert
    assert result.exit_code != 0
    assert 'Persona "non_existent_persona" does not exist' in result.stdout
