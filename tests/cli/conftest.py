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
    config_file = mock_home / 'config.yaml'
    config_data = {'type': 'local', 'root': str(mock_home)}
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    index_file = mock_home / 'index.json'
    with open(index_file, 'w') as f:
        import json

        json.dump({'personas': {}, 'skills': {}}, f)

    return config_file
