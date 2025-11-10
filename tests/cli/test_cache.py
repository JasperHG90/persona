import pytest
from pathlib import Path
from typer.testing import CliRunner

from persona.cli.cache import app
from persona.cache import PERSONA_CACHE


@pytest.fixture(autouse=True)
def create_cache_dir():
    PERSONA_CACHE.mkdir(parents=True, exist_ok=True)
    yield
    import shutil
    shutil.rmtree(PERSONA_CACHE)


def test_clean_cache(runner: CliRunner) -> None:
    # Arrange
    (PERSONA_CACHE / "test_file").touch()

    # Act
    result = runner.invoke(app, ["clean"])

    # Assert
    assert result.exit_code == 0
    assert "Cache cleaned" in result.stdout
    assert not (PERSONA_CACHE / "test_file").exists()


def test_clean_cache_empty(runner: CliRunner) -> None:
    # Arrange
    if any(PERSONA_CACHE.iterdir()):
        for item in PERSONA_CACHE.iterdir():
            if item.is_dir():
                item.rmdir()
            else:
                item.unlink()


    # Act
    result = runner.invoke(app, ["clean"])

    # Assert
    assert result.exit_code == 0
    assert "Cache is empty" in result.stdout


def test_cache_dir(runner: CliRunner) -> None:
    # Arrange
    # Act
    result = runner.invoke(app, ["dir"])

    # Assert
    assert result.exit_code == 0
    assert str(PERSONA_CACHE) in result.stdout
