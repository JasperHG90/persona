import logging
import hashlib
from typing import Any, Literal, TYPE_CHECKING, cast

import orjson
from pydantic import RootModel, Field


if TYPE_CHECKING:
    from persona.storage.filestore import BaseFileStore
    from persona.storage.metastore import CursorLikeMetaStoreEngine, BaseMetaStoreSession


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

    def __init__(self, file_store: 'BaseFileStore', meta_store_engine: 'CursorLikeMetaStoreEngine'):
        self._logger = logging.getLogger('persona.storage.transaction.Transaction')
        self._file_store = file_store
        self._meta_store_engine = meta_store_engine
        self._log: list[tuple[Literal['restore', 'delete'], str, Any]] = []
        self._hashes = TemplateHashValues()

    def _add_log_entry(
        self, action: Literal['restore', 'delete'], key: str, data: Any = None
    ) -> None:
        self._logger.debug(f'Logging action: {action} for key: {key}')
        self._log.append((action, key, data))

    def _add_file_hash(self, file: str, content: bytes) -> None:
        self._hashes.add(file, content)

    def _process_metadata(
        self,
    ) -> dict[str, list[str] | list[dict[str, str | list[str]]] | str] | None:
        types: list[str] = []
        deletes: list[str] = []
        upserts: list[dict[str, str | list[str]]] = []

        for action, entry in self._meta_store_engine._metadata:
            if entry.uuid is None:
                entry.update('uuid', self.transaction_id)
            if action == 'delete':
                if entry.name is not None:
                    deletes.append(entry.name)
            elif action == 'upsert':
                upserts.append(entry.model_dump(exclude={'type'}))
            if entry.type is not None:
                types.append(entry.type)

        type_ = list(set(types))
        if len(type_) > 1:
            raise ValueError('All index entries must have the same type for a single transaction.')
        elif len(type_) == 0:
            self._logger.debug('No metadata to update in index.')
            return

        return {
            'type': type_[0],
            'deletes': deletes,
            'upserts': upserts,
        }

    def _update_index(
        self,
        meta_store: 'BaseMetaStoreSession',
        upserts: list[dict[str, str | list[str]]],
        deletes: list[str],
        type: str,
    ) -> None:
        """Update the index with the new or updated template entry."""
        if upserts:
            meta_store.upsert(
                type,
                upserts,
            )
        if deletes:
            meta_store.remove(
                type,
                deletes,
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
                self._file_store._save(key, data)
            elif action == 'delete':
                self._file_store._delete(key, recursive=False)

    def __enter__(self) -> 'Transaction':
        self._logger.debug('Starting transaction...')
        self._file_store._transaction = self
        self._meta_store_engine._transaction = self

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._logger.debug('Ending transaction...')

        try:
            # If any error occurred, roll back changes on the FileStore
            if exc_type is not None:
                self._logger.error(f'Transaction failed with exception: {exc_value}')
                self._logger.debug('Performing rollback due to exception...')
                self.rollback()
                return

            # Try to write updates/deletes to MetaStore. If that fails,
            # roll back changes on the FileStore
            try:
                metadata = self._process_metadata()
                if metadata is None:
                    self._logger.debug('No metadata changes to process during transaction commit.')
                    return
                # NB: Save manifests (index entries) to file store
                # Add them using `.save()` to ensure they are part of the transaction
                # And are rolled back if needed
                for entry in cast(dict, metadata).get('upserts', []):
                    template_root = entry['files'][0].rsplit('/', 1)[0]
                    self._file_store.save(
                        f'{template_root.rstrip("/")}/.manifest.json',
                        orjson.dumps(
                            {k: v for k, v in entry.items() if k != 'embedding'},
                            option=orjson.OPT_INDENT_2,
                        ),
                    )
                # NB: for DuckDB, closing the `connected` object will trigger an export of the
                #  data to storage as parquet
                with self._meta_store_engine.open(bootstrap=True) as connected:
                    with connected.session() as session:
                        self._update_index(
                            meta_store=session,
                            upserts=cast(list[dict[str, str | list[str]]], metadata['upserts']),
                            deletes=cast(list[str], metadata['deletes']),
                            type=cast(str, metadata['type']),
                        )
            except Exception as e:
                self._logger.error(f'Failed to update index during transaction commit: {e}')
                self._logger.debug('Performing rollback due to index update failure...')
                self.rollback()
                raise e

        finally:
            # Clear transaction references
            self._file_store._transaction = None
            self._meta_store_engine._transaction = None

            self._log = []
