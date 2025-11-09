from .base import StorageBackend as StorageBackend, Transaction as Transaction
from .local import LocalStorageBackend as LocalStorageBackend
from .models import Index as Index, IndexEntry as IndexEntry, SubIndex as SubIndex

from persona import config

BACKEND_MAP = {config.LocalStorageConfig: LocalStorageBackend}


def get_storage_backend(config: config.AnyStorage) -> StorageBackend:
    backend_class = BACKEND_MAP.get(type(config))
    if not backend_class:
        raise ValueError(f'No storage backend found for config type: {type(config)}')
    return backend_class(config)
