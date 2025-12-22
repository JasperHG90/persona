import os
import logging
import hashlib
import pathlib as plb
from typing import Generic, TypeVar, Any, Literal, cast, BinaryIO
from abc import ABCMeta, abstractmethod

import orjson
from fsspec import AbstractFileSystem
from pydantic import RootModel, Field

from persona.config import BaseStorageConfig

T = TypeVar('T', bound=BaseStorageConfig)


class TemplateHashValues(RootModel[dict[str, str]]):
    root: dict[str, str] = Field(default_factory=dict)

    def _hash_content(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def add(self, file: str, content: bytes) -> None:
        self.root[file] = self._hash_content(content)

    def hash(self, exclude: set[str] | None = None) -> str:
        model_dump = {
            k: v for k, v in self.model_dump().items() if exclude is None or k not in exclude
        }
        return self._hash_content(orjson.dumps(model_dump, option=orjson.OPT_SORT_KEYS))


class Transaction:
    """A context manager for handling transactions in storage backends."""

    def __init__(self, storage_backend: 'StorageBackend'):
        self._logger = logging.getLogger('persona.storage.Transaction')
        self._storage = storage_backend
        self._index_backup: plb.Path = plb.Path(
            self._storage.join_path(f'./.persona/{self._storage.config.index}.bak')
        )
        self._index: plb.Path = plb.Path(
            self._storage.join_path(f'./.persona/{self._storage.config.index}')
        )

        self._log: list[tuple[Literal['restore', 'delete'], str, Any]] = []
        self._hashes = TemplateHashValues()

    def _add_log_entry(
        self, action: Literal['restore', 'delete'], key: str, data: Any = None
    ) -> None:
        self._logger.debug(f'Logging action: {action} for key: {key}')
        self._log.append((action, key, data))

    def _add_file_hash(self, file: str, content: bytes) -> None:
        self._hashes.add(file, content)

    @property
    def transaction_id(self) -> str:
        """Generate a unique transaction ID based on the file hashes."""
        return self._hashes.hash(exclude=set('index.json'))

    def rollback(self) -> None:
        """Rollback all changes made during the transaction."""
        self._logger.debug('Rolling back transaction...')

        for action, key, data in reversed(self._log):
            # NB: use internal methods to avoid logging during rollback
            if action == 'restore':
                self._storage._save(key, data)
            elif action == 'delete':
                self._storage._delete(key, recursive=False)

    def __enter__(self) -> 'Transaction':
        self._logger.debug('Starting transaction...')
        self._storage._transaction = self

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._logger.debug('Ending transaction...')
        self._storage._transaction = None

        if exc_type is not None:
            self.rollback()

        self._index_backup.unlink(missing_ok=True)

        self._undo_log = []


class StorageBackend(Generic[T], metaclass=ABCMeta):
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
