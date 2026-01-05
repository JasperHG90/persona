import os
import pytest
from pathlib import Path
import yaml


@pytest.fixture(scope='function', autouse=True)
def init_persona_env(tmp_path):
    """
    Session-scoped fixture to initialize the Persona environment in a temporary directory.
    This ensures that tests run in an isolated environment and do not interfere with the user's
    local configuration or each other (if they used the system default).
    """
    temp_dir = Path(tmp_path)

    # Define paths
    config_path = temp_dir / '.persona.config.yaml'
    persona_root = temp_dir / '.persona'
    persona_root.mkdir(parents=True, exist_ok=True)
    (persona_root / 'index').mkdir(parents=True, exist_ok=True)
    (persona_root / 'roles').mkdir(parents=True, exist_ok=True)
    (persona_root / 'skills').mkdir(parents=True, exist_ok=True)

    # Store original env vars
    original_env = {
        key: os.environ.get(key)
        for key in [
            'PERSONA_CONFIG_PATH',
            'XDG_DATA_HOME',
            'XDG_CACHE_HOME',
            'XDG_CONFIG_HOME',
            'PERSONA_ROOT',
        ]
    }

    # Set environment variables for isolation
    os.environ['PERSONA_CONFIG_PATH'] = str(config_path)
    os.environ['XDG_DATA_HOME'] = str(temp_dir / '.local' / 'share')
    os.environ['XDG_CACHE_HOME'] = str(temp_dir / '.cache')
    os.environ['XDG_CONFIG_HOME'] = str(temp_dir / '.config')
    # Setting PERSONA_ROOT ensures the default root in PersonaConfig points here
    os.environ['PERSONA_ROOT'] = str(persona_root)

    # Create default configuration
    config_data = {
        'root': str(persona_root),
        'file_store': {'type': 'local', 'root': str(persona_root)},
        'meta_store': {'type': 'duckdb', 'root': str(persona_root)},
    }
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)

    yield config_path

    # Restore original env vars
    for key, value in original_env.items():
        if value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = value
