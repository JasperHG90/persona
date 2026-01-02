import pytest
from typer.testing import CliRunner
from pathlib import Path
import yaml


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_home(tmp_path: Path) -> Path:
    home_path = tmp_path / '.persona'
    home_path.mkdir(parents=True, exist_ok=True)
    return home_path


@pytest.fixture
def mock_config_file(mock_home: Path) -> Path:
    config_file = mock_home.parent / '.persona.config.yaml'
    config_data = {'type': 'local', 'root': str(mock_home), 'index': 'index'}
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    index = mock_home / 'index'
    index.mkdir(parents=True, exist_ok=True)

    return config_file
