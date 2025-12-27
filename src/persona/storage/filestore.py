import os
import logging
from typing import Generic, TypeVar, cast, BinaryIO, TYPE_CHECKING
from abc import ABCMeta, abstractmethod

from fsspec import AbstractFileSystem
from fsspec.implementations.local import LocalFileSystem

from persona.config import BaseFileStoreConfig, LocalFileStoreConfig

if TYPE_CHECKING:
    from .transaction import Transaction

T = TypeVar('T', bound=BaseFileStoreConfig)


class BaseFileStore(Generic[T], metaclass=ABCMeta):
    def __init__(self, config: T):
        self.config = config
        self._logger = logging.getLogger(f'persona.storage.{self.__class__.__name__}')
        self._logger.debug(f'Initialized storage backend with config: {self.config}')
        self._fs = self.initialize()
        self._logger.debug(f'Storage backend filesystem initialized: {self._fs}')

        self._transaction: Transaction | None = None

    @abstractmethod
    def initialize(self) -> AbstractFileSystem:
        """Initialize the storage backend and return the filesystem object."""
        pass

    def join_path(self, key: str) -> str:
        """Join root path with a key

        Args:
            key (str): relative path to the file, e.g. path/to/file.txt

        Returns:
            str: joined path, e.g. /home/vscode/workspace/path/to/file.txt
        """
        return os.path.join(str(self.config.root), key)

    def _save(self, key: str, data: bytes) -> None:
        """Save data to the storage backend without transaction logging."""
        fp = self.join_path(key)
        self._logger.debug(f'Saving data to path: {fp}')
        self._fs.makedirs(self._fs._parent(fp), exist_ok=True)
        with cast(BinaryIO, self._fs.open(fp, 'wb')) as f:
            f.write(data)

    def save(self, key: str, data: bytes) -> None:
        """
        Save data to the storage backend.

        Args:
            key: The identifier for the data.
            data: The string data to be saved.
        """
        if self._transaction:
            if self.exists(key):
                existing_data = self.load(key)
                self._transaction._add_log_entry('restore', key, existing_data)
            else:
                self._transaction._add_log_entry('delete', key)
            # Keep track of new file hashes for idempotent transaction id
            self._transaction._add_file_hash(key, data)
        self._save(key, data)

    def _delete(self, key: str, recursive: bool) -> None:
        """Delete data from the storage backend without transaction logging."""
        self._logger.debug(f'Deleting data with key: {key}')
        if self.exists(key):
            self._fs.rm(self.join_path(key), recursive=recursive)

    def delete(self, key: str, recursive: bool = False) -> None:
        """
        Delete data from the storage backend.

        Args:
            key: The identifier for the data to be deleted.
        """
        if self._transaction:
            if self.exists(key):
                if not self._fs.isdir(self.join_path(key)):
                    existing_data = self.load(key)
                    self._transaction._add_log_entry('restore', key, existing_data)
                    self._transaction._add_file_hash(key, existing_data)
        self._delete(key, recursive=recursive)

    def load(self, key: str) -> bytes:
        """
        Load data from the storage backend.

        Args:
            key: The identifier for the data.

        Returns:
            The loaded string data.
        """
        fp = self.join_path(key)
        self._logger.debug(f'Loading data from path: {fp}')
        with cast(BinaryIO, self._fs.open(fp, 'rb')) as f:
            return f.read()

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the storage backend.

        Args:
            key: The identifier for the data.

        Returns:
            True if the key exists, False otherwise.
        """
        self._logger.debug(f'Checking for existence of key: {key}')
        return self._fs.exists(self.join_path(key))

    def is_dir(self, key: str) -> bool:
        """
        Check if a key is a directory in the storage backend.

        Args:
            key: The identifier for the data.

        Returns:
            True if the key is a directory, False otherwise.
        """
        return self._fs.isdir(self.join_path(key))

    def glob(self, pattern: str) -> list[str]:
        """
        Glob for files matching a pattern in the storage backend.

        Args:
            pattern: The glob pattern to match files.

        Returns:
            A list of matching file paths.
        """
        return cast(list[str], self._fs.glob(self.join_path(pattern)))


class LocalFileStore(BaseFileStore[LocalFileStoreConfig]):
    def initialize(self) -> LocalFileSystem:
        return LocalFileSystem()
