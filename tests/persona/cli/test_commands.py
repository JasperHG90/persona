import pathlib as plb
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from persona.cli import app


@pytest.fixture
def mock_api():
    with patch('persona.cli.commands.PersonaAPI') as mock_api_class:
        mock = MagicMock()
        mock_api_class.return_value = mock
        yield mock


def test_list_templates_personas(runner: CliRunner, mock_api: MagicMock) -> None:
    # Arrange
    # API returns dicts, not objects
    mock_api.list_templates.return_value = [
        {'name': 'test_persona', 'description': 'A test persona', 'uuid': '1234'}
    ]

    # Act
    result = runner.invoke(app, ['roles', 'list'])

    # Assert
    assert result.exit_code == 0
    assert 'test_persona' in result.stdout
    mock_api.list_templates.assert_called_once_with(
        'roles', columns=['name', 'description', 'uuid']
    )


def test_list_templates_empty(runner: CliRunner, mock_api: MagicMock) -> None:
    # Arrange
    mock_api.list_templates.return_value = []

    # Act
    result = runner.invoke(app, ['roles', 'list'])

    # Assert
    assert result.exit_code == 0
    mock_api.list_templates.assert_called_once_with(
        'roles', columns=['name', 'description', 'uuid']
    )


def test_copy_template(runner: CliRunner, mock_api: MagicMock, tmp_path: plb.Path) -> None:
    # Arrange
    template_path = tmp_path / 'PERSONA.md'
    template_path.write_text('---\nname: new_persona\ndescription: A new persona\n---\n')

    # Act
    result = runner.invoke(
        app,
        ['roles', 'register', str(template_path)],
    )

    # Assert
    assert result.exit_code == 0
    mock_api.publish_template.assert_called_once()


def test_remove_template(runner: CliRunner, mock_api: MagicMock) -> None:
    # Act
    result = runner.invoke(app, ['roles', 'remove', 'test_persona'])

    # Assert
    assert result.exit_code == 0
    assert 'Template "test_persona" has been removed' in result.stdout
    mock_api.delete_template.assert_called_once_with('test_persona', 'roles')


def test_remove_template_not_found(runner: CliRunner, mock_api: MagicMock) -> None:
    # Arrange
    mock_api.delete_template.side_effect = ValueError(
        'Persona "non_existent_persona" does not exist'
    )

    # Act
    result = runner.invoke(app, ['roles', 'remove', 'non_existent_persona'])

    # Assert
    assert result.exit_code != 0
    assert 'Persona "non_existent_persona" does not exist' in result.stdout
