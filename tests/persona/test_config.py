import pathlib as plb
from typing import Any

import pytest

from persona.config import (
    BaseFileStoreConfig,
    DuckDBMetaStoreConfig,
    FileStoreBasedMetaStoreConfig,
    LocalFileStoreConfig,
    PersonaConfig,
    parse_persona_config,
)


# --- BaseFileStoreConfig Tests ---


def test_base_file_store_paths() -> None:
    config = BaseFileStoreConfig(root='/tmp/persona')
    assert config.roles_dir == '/tmp/persona/roles'
    assert config.skills_dir == '/tmp/persona/skills'


def test_base_file_store_paths_strip_slash() -> None:
    config = BaseFileStoreConfig(root='/tmp/persona/')
    assert config.roles_dir == '/tmp/persona/roles'
    assert config.skills_dir == '/tmp/persona/skills'


def test_base_file_store_no_root() -> None:
    config = BaseFileStoreConfig()
    # root is None by default
    with pytest.raises(ValueError, match='Root path is not set'):
        _ = config.roles_dir
    with pytest.raises(ValueError, match='Root path is not set'):
        _ = config.skills_dir


# --- FileStoreBasedMetaStoreConfig Tests ---


def test_meta_store_paths() -> None:
    config = FileStoreBasedMetaStoreConfig(root='/tmp/persona', index_folder='idx')
    assert config.index_path == '/tmp/persona/idx'
    assert config.roles_index_path == '/tmp/persona/idx/roles.parquet'
    assert config.skills_index_path == '/tmp/persona/idx/skills.parquet'


def test_meta_store_no_root() -> None:
    config = FileStoreBasedMetaStoreConfig()
    with pytest.raises(ValueError, match='Root path is not set'):
        _ = config.index_path
    with pytest.raises(ValueError, match='Root path is not set'):
        _ = config.roles_index_path
    with pytest.raises(ValueError, match='Root path is not set'):
        _ = config.skills_index_path


# --- PersonaConfig Tests ---


def test_persona_config_defaults() -> None:
    config = PersonaConfig()
    # Check defaults
    assert config.root is not None
    assert 'persona' in config.root  # Should be user data dir

    assert isinstance(config.file_store, LocalFileStoreConfig)
    assert config.file_store.type == 'local'
    # Should have inherited root
    assert config.file_store.root == config.root

    assert isinstance(config.meta_store, DuckDBMetaStoreConfig)
    assert config.meta_store.type == 'duckdb'
    # Should have inherited root
    assert config.meta_store.root == config.root


def test_sync_root_paths_propagation() -> None:
    """Test that the top-level root propagates to sub-configs if they are None."""
    root_path = '/custom/root'
    config = PersonaConfig(root=root_path)

    assert config.file_store.root == root_path
    assert config.meta_store.root == root_path


def test_sync_root_paths_no_overwrite() -> None:
    """Test that explicit roots in sub-configs are NOT overwritten."""
    root_path = '/custom/root'
    file_store_root = '/other/store'

    # We must explicitly provide the sub-config objects to override their defaults
    file_store = LocalFileStoreConfig(root=file_store_root)

    config = PersonaConfig(root=root_path, file_store=file_store)

    assert config.root == root_path
    assert config.file_store.root == file_store_root
    # meta_store should still inherit since we didn't override it
    assert config.meta_store.root == root_path


def test_root_normalized() -> None:
    config = PersonaConfig(root='~/.persona-test')
    normalized = config.root_normalized
    assert str(plb.Path.home()) in normalized
    assert '.persona-test' in normalized


# --- parse_persona_config Tests ---


def test_parse_persona_config_defaults() -> None:
    """Test that missing types are injected."""
    data: dict[str, Any] = {'root': '/tmp', 'file_store': {}, 'meta_store': {}}

    config = parse_persona_config(data)

    assert isinstance(config.file_store, LocalFileStoreConfig)
    assert config.file_store.type == 'local'

    assert isinstance(config.meta_store, DuckDBMetaStoreConfig)
    assert config.meta_store.type == 'duckdb'


def test_parse_persona_config_valid() -> None:
    data = {
        'root': '/tmp',
        'file_store': {'type': 'local', 'root': '/fs'},
        'meta_store': {'type': 'duckdb', 'root': '/ms', 'index_folder': 'i'},
    }
    config = parse_persona_config(data)

    assert config.root == '/tmp'
    assert config.file_store.root == '/fs'
    assert config.meta_store.root == '/ms'
    assert config.meta_store.index_folder == 'i'
