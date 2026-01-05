import pytest
from persona.config import (
    LocalFileStoreConfig,
    DuckDBMetaStoreConfig,
    BaseFileStoreConfig,
    BaseMetaStoreConfig,
)
from persona.storage import get_file_store_backend, get_meta_store_backend
from persona.storage.filestore import LocalFileStore
from persona.storage.metastore import DuckDBMetaStoreEngine


def test_get_file_store_backend_local(tmp_path) -> None:
    config = LocalFileStoreConfig(root=str(tmp_path))
    backend = get_file_store_backend(config)
    assert isinstance(backend, LocalFileStore)
    assert backend.config == config


def test_get_file_store_backend_invalid() -> None:
    class InvalidConfig(BaseFileStoreConfig):
        type: str = 'invalid'
        root: str = 'path'

    with pytest.raises(ValueError, match='No file store found'):
        get_file_store_backend(InvalidConfig(type='invalid', root='path'))


def test_get_meta_store_backend_duckdb(tmp_path) -> None:
    config = DuckDBMetaStoreConfig(
        roles_index_path=str(tmp_path / 'roles'), skills_index_path=str(tmp_path / 'skills')
    )
    backend = get_meta_store_backend(config)
    assert isinstance(backend, DuckDBMetaStoreEngine)
    assert backend._config == config


def test_get_meta_store_backend_invalid() -> None:
    class InvalidMetaConfig(BaseMetaStoreConfig):
        type: str = 'invalid'

    with pytest.raises(ValueError, match='No meta store found'):
        get_meta_store_backend(InvalidMetaConfig(type='invalid'))
