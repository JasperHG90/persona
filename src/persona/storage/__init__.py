from .file_store import (
    FileStore as FileStore,
    LocalFileStore as LocalFileStore,
)
from .meta_store import (
    MetaStore as MetaStore,
    DuckDBMetaStore as DuckDBMetaStore
)
from .models import IndexEntry as IndexEntry

from persona import config

FILESTORE_BACKEND_MAP = {config.LocalFileStoreConfig: LocalFileStore}
METASTORE_BACKEND_MAP = {config.DuckDBMetaStoreConfig: DuckDBMetaStore}


def get_file_store_backend(config: config.FileStoreBackend) -> FileStore:
    file_store_class = FILESTORE_BACKEND_MAP.get(type(config))
    if not file_store_class:
        raise ValueError(f'No file store found for config type: {type(config)}')
    return file_store_class(config)


def get_meta_store_backend(config: config.MetaStoreBackend) -> MetaStore:
    meta_store_class = METASTORE_BACKEND_MAP.get(type(config))
    if not meta_store_class:
        raise ValueError(f"No meta store found for config type: {type(config)}")
    return meta_store_class(config)
