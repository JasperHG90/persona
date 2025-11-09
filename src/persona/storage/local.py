from fsspec.implementations.local import LocalFileSystem

from .base import StorageBackend
from persona.config import LocalStorageConfig


class LocalStorageBackend(StorageBackend[LocalStorageConfig]):
    def initialize(self) -> LocalFileSystem:
        return LocalFileSystem()
