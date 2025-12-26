from persona.storage.filestore import (
    BaseFileStore as BaseFileStore,
    LocalFileStore as LocalFileStore,
)
from persona.storage.metastore import (
    BaseMetaStore as BaseMetaStore,
    CursorLikeMetaStore as CursorLikeMetaStore,
    CursorLikeMetaStoreEngine as CursorLikeMetaStoreEngine,
    DuckDBMetaStoreEngine as DuckDBMetaStoreEngine,
)
from persona.storage.models import IndexEntry as IndexEntry
from persona.storage.transaction import Transaction as Transaction

from persona import config

FILESTORE_BACKEND_MAP = {config.LocalFileStoreConfig: LocalFileStore}
METASTORE_BACKEND_MAP = {config.DuckDBMetaStoreConfig: DuckDBMetaStoreEngine}


def get_file_store_backend(config: config.FileStoreBackend) -> BaseFileStore:
    file_store_class = FILESTORE_BACKEND_MAP.get(type(config))
    if not file_store_class:
        raise ValueError(f'No file store found for config type: {type(config)}')
    return file_store_class(config)


def get_meta_store_backend(config: config.MetaStoreBackend) -> CursorLikeMetaStoreEngine:
    meta_store_class = METASTORE_BACKEND_MAP.get(type(config))
    if not meta_store_class:
        raise ValueError(f'No meta store found for config type: {type(config)}')
    return meta_store_class(config)
