import logging
import hashlib
from typing import Any, Literal, TYPE_CHECKING

import orjson
from pydantic import RootModel, Field

if TYPE_CHECKING:
    from .file_store import FileStore
    from .meta_store import MetaStore


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

    def __init__(self, storage_backend: FileStore, vector_db: MetaStore):
        self._logger = logging.getLogger('persona.storage.transaction.Transaction')
        self._storage = storage_backend
        self._db = vector_db
        self._log: list[tuple[Literal['restore', 'delete'], str, Any]] = []
        self._hashes = TemplateHashValues()

    def _add_log_entry(
        self, action: Literal['restore', 'delete'], key: str, data: Any = None
    ) -> None:
        self._logger.debug(f'Logging action: {action} for key: {key}')
        self._log.append((action, key, data))

    def _add_file_hash(self, file: str, content: bytes) -> None:
        self._hashes.add(file, content)

    def _update_index(self) -> None:
        """Update the index with the new or updated template entry."""
        type_ = list(set(entry.type for _, entry in self._db._metadata))
        if len(type_) > 1:
            raise ValueError('All index entries must have the same type for a single transaction.')
        elif len(type_) == 0:
            self._logger.debug('No metadata to update in index.')
            return
        deletes = []
        upserts = []

        for action, entry in self._db._metadata:
            if entry.uuid is None:
                entry.update('uuid', self.transaction_id)
            if action == 'delete':
                deletes.append(entry)
            elif action == 'upsert':
                upserts.append(entry)

        if upserts:
            self._db.upsert(
                'skills' if type_[0] == 'skill' else 'roles',
                [entry.model_dump(exclude=['type']) for entry in upserts],
            )
        if deletes:
            self._db.remove(
                'skills' if type_[0] == 'skill' else 'roles',
                [entry.name for entry in deletes if entry.name is not None],
            )

    @property
    def transaction_id(self) -> str:
        """Generate a unique transaction ID based on the file hashes."""
        return self._hashes.hash()

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
        self._db._transaction = self

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._logger.debug('Ending transaction...')
        self._storage._transaction = None

        if exc_type is not None:
            self._logger.error(f'Transaction failed with exception: {exc_value}')
            self._logger.debug('Performing rollback due to exception...')
            self.rollback()

        try:
            self._update_index()
        except Exception as e:
            self._logger.error(f'Failed to update index during transaction commit: {e}')
            self._logger.debug('Performing rollback due to index update failure...')
            self.rollback()
            raise e

        self._undo_log = []
