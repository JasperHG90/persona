from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from persona.cli.utils import create_cli
from persona.cli.commands import TemplateTypeEnum


def test_create_cli_list(runner: CliRunner) -> None:
    # Arrange
    app = create_cli('test', TemplateTypeEnum.PERSONA, 'help', 'desc')

    # Act
    with patch('persona.cli.utils.list_templates') as mock_list:
        result = runner.invoke(app, ['list'])

        # Assert
        assert result.exit_code == 0
        mock_list.assert_called_once()


def test_create_cli_register_local(runner: CliRunner, tmp_path: Path) -> None:
    # Arrange
    app = create_cli('test', TemplateTypeEnum.PERSONA, 'help', 'desc')
    template_path = tmp_path / 'PERSONA.md'
    template_path.touch()

    # Act
    with patch('persona.cli.utils.copy_template') as mock_copy:
        result = runner.invoke(app, ['register', str(template_path)])

        # Assert
        assert result.exit_code == 0
        mock_copy.assert_called_once()


def test_create_cli_register_github(runner: CliRunner) -> None:
    # Arrange
    app = create_cli('test', TemplateTypeEnum.PERSONA, 'help', 'desc')

    # Act
    with patch('persona.cli.utils.download_and_cache_github_repo') as mock_download:
        with patch('persona.cli.utils.copy_template') as mock_copy:
            result = runner.invoke(
                app,
                [
                    'register',
                    'some/path',
                    '--github-url',
                    'https://github.com/user/repo/tree/main',
                ],
            )

            # Assert
            assert result.exit_code == 0
            mock_download.assert_called_once()
            mock_copy.assert_called_once()


def test_create_cli_remove(runner: CliRunner) -> None:
    # Arrange
    app = create_cli('test', TemplateTypeEnum.PERSONA, 'help', 'desc')

    # Act
    with patch('persona.cli.utils.remove_template') as mock_remove:
        result = runner.invoke(app, ['remove', 'test_persona'])

        # Assert
        assert result.exit_code == 0
        mock_remove.assert_called_once()
