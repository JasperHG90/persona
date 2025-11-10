import pathlib as plb

import pytest
from pydantic import ValidationError

from persona.config import (
    BaseStorageConfig,
    LocalStorageConfig,
    parse_storage_config,
)


def test_base_storage_config_defaults() -> None:
    # Arrange
    # Act
    config = BaseStorageConfig()

    # Assert
    assert config.root == str(plb.Path.home() / '.persona')
    assert config.index == 'index.json'


def test_base_storage_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_STORAGE_ROOT', '/test/root')
    monkeypatch.setenv('PERSONA_STORAGE_INDEX', 'test_index.json')

    # Act
    config = BaseStorageConfig()

    # Assert
    assert config.root == '/test/root'
    assert config.index == 'test_index.json'


def test_base_storage_config_index_path() -> None:
    # Arrange
    config = BaseStorageConfig(root='/test/root', index='test_index.json')

    # Act
    index_path = config.index_path

    # Assert
    assert index_path == '/test/root/test_index.json'


def test_local_storage_config_type() -> None:
    # Arrange
    # Act
    config = LocalStorageConfig(type='local')

    # Assert
    assert config.type == 'local'


def test_parse_storage_config_with_type() -> None:
    # Arrange
    data = {'type': 'local', 'root': '/test'}

    # Act
    config = parse_storage_config(data)

    # Assert
    assert isinstance(config.root, LocalStorageConfig)
    assert config.root.type == 'local'
    assert config.root.root == '/test'


def test_parse_storage_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv('PERSONA_STORAGE_TYPE', 'local')
    data = {'root': '/test'}

    # Act
    config = parse_storage_config(data)

    # Assert
    assert isinstance(config.root, LocalStorageConfig)
    assert config.root.type == 'local'
    assert config.root.root == '/test'


def test_parse_storage_config_validation_error() -> None:
    # Arrange
    data = {'root': '/test'}

    # Act & Assert
    with pytest.raises(ValidationError):
        parse_storage_config(data)
