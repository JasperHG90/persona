"""
This module implements a bridge pattern for different metastore backends.
The Engine class can vary (e.g. DuckDB, Postgres, etc.), while the MetaStoreLogic
class provides the business logic for interacting with the metastore.
"""

import logging
from typing import Generic, TypeVar, Generator, Literal, TYPE_CHECKING, Self
import pathlib as plb
from abc import abstractmethod, ABCMeta
from contextlib import contextmanager

import duckdb
from platformdirs import user_cache_dir

from persona.config import BaseMetaStoreConfig, DuckDBMetaStoreConfig
from persona.storage.models import IndexEntry
from persona.storage.metastore.utils import CursorLike
from persona.storage.metastore.session import CursorLikeMetaStoreSession

if TYPE_CHECKING:
    from persona.storage.transaction import Transaction

T = TypeVar('T', bound=BaseMetaStoreConfig)


class CursorLikeMetaStoreEngine(Generic[T], metaclass=ABCMeta):
    def __init__(self, config: T):
        self._logger = logging.getLogger(
            f'persona.storage.metastore.engine.{self.__class__.__name__}'
        )
        self._config: T = config
        self._metadata: list[tuple[Literal['upsert', 'delete'], IndexEntry]] = []
        self._transaction: Transaction | None = None
        self._bootstrapped: bool = False

    @abstractmethod
    def bootstrap(self) -> Self:
        """Bootstraps the metastore backend, creating necessary tables or structures."""
        ...

    @abstractmethod
    def connect(self) -> Self:
        """Connect to the metastore backend."""
        ...

    @abstractmethod
    def close(self):
        """Close the connection to the metastore backend."""
        ...

    @abstractmethod
    def get_cursor(self) -> CursorLike:
        """Get a new cursor for executing queries."""
        ...

    @contextmanager
    def open(self, bootstrap: bool = False) -> Generator[Self, None, None]:
        """Connect to a metastore backend and close the connection gracefully

        Args:
            bootstrap (bool, optional): Whether to bootstrap the metastore upon connection. Defaults to False
        """
        try:
            self.connect()
            if bootstrap:
                self.bootstrap()
            yield self
        finally:
            self.close()
            self._bootstrapped = False

    @contextmanager
    def read_session(self) -> Generator[CursorLikeMetaStoreSession, None, None]:
        """Start a new read-only session returning a cursor, and close it upon exiting the context manager.

        Note: the read-only session pertains only to the in-memory duckdb database. This avoids the overhead of beginning/committing transactions
        for read-only in-memory operations.

        Yields:
            Generator[CursorLikeMetaStore, None, None]: a cursor-like object containing methods like: execute(), fetchone(), fetchall()
        """
        self._logger.debug('Starting new read-only metastore session ...')
        cursor = self.get_cursor()
        try:
            yield CursorLikeMetaStoreSession(cursor)
        finally:
            self._logger.debug('Closing read-only session ...')
            cursor.close()

    @contextmanager
    def session(self) -> Generator[CursorLikeMetaStoreSession, None, None]:
        """Start a new session returning a cursor, and commit / close it upon exiting the context manager

        Yields:
            Generator[CursorLikeMetaStore, None, None]: a cursor-like object containing methods like: commit(), rollback(), execute(), fetchone(), fetchall()
        """
        self._logger.debug('Starting new metastore session ...')
        cursor = self.get_cursor()
        cursor.begin()
        try:
            yield CursorLikeMetaStoreSession(cursor)
            cursor.commit()
        except Exception as e:
            self._logger.error(f'Session error: {e}. Rolling back transaction.')
            cursor.rollback()
            raise
        finally:
            self._logger.debug('Closing session ...')
            cursor.close()

    def index(self, entry: IndexEntry) -> None:
        """Stage metadata to be written to the metastore"""
        if self._transaction:
            self._metadata.append(('upsert', entry))
        else:
            self._logger.warning('Attempted to index entry outside of transaction.')

    def deindex(self, entry: IndexEntry) -> None:
        """Stage metadata deletion from the metastore"""
        if self._transaction:
            self._metadata.append(('delete', entry))
        else:
            self._logger.warning('Attempted to deindex entry outside of transaction.')


class DuckDBMetaStoreEngine(CursorLikeMetaStoreEngine[DuckDBMetaStoreConfig]):
    def __init__(
        self, config: DuckDBMetaStoreConfig, read_only: bool = True, tables: list[str] | None = None
    ):
        super().__init__(config=config)

        self._conn: duckdb.DuckDBPyConnection | None = None
        self._logger.debug(
            f'Engine is in {"read only" if read_only else "write"} mode. Updates {"will not" if read_only else "will"} be persisted ...'
        )
        self._read_only = read_only
        if tables is None:
            self._tables = ['roles', 'skills']
        else:
            self._tables = tables

    def bootstrap(self):
        """Bootstraps the in-memory database using existing indexes if available."""
        if self._conn is None:
            raise RuntimeError('No database connection; call connect() first.')
        if self._bootstrapped:
            self._logger.debug('Metastore already bootstrapped; skipping ...')
            return self
        for table in self._tables:
            self._conn.execute(
                f'CREATE TABLE IF NOT EXISTS {table} (name VARCHAR PRIMARY KEY, date_created TIMESTAMP, description VARCHAR, tags VARCHAR[], uuid VARCHAR(32), etag VARCHAR(32), files VARCHAR[], embedding FLOAT[384])'
            )
            path_ = getattr(self._config, f'{table}_index_path')
            try:
                self._logger.debug(f'Loading existing {table} index from disk ...')
                self._conn.execute(f"INSERT INTO {table} SELECT * FROM read_parquet('{path_}');")
                self._bootstrapped = True
            except duckdb.BinderException as e:
                self._logger.error(
                    'Schema mismatch when loading index. Please reindex the metastore using `persona reindex`'
                )
                raise e
            except duckdb.IOException:
                self._logger.warning(
                    f'No existing {table} index found at {path_}: Table initialized empty ...'
                )
                self._bootstrapped = True
            except Exception as e:
                self._logger.error('Unknown error when loading existing index.')
                raise e
        return self

    def _export_tables(self):
        """Exports the in-memory database tables to disk."""
        if self._conn is None:
            raise RuntimeError('No database connection; call connect() first.')
        for table in self._tables:
            path_ = getattr(self._config, f'{table}_index_path')
            self._logger.debug(f'Exporting {table} index to disk at: {path_} ...')
            self._conn.execute(f"""COPY "{table}" TO '{path_}' (FORMAT PARQUET);""")

    def connect(self) -> Self:
        if self._conn is not None:
            self._logger.debug(
                'DuckDB connection already established. To open a new connection, close the existing one first.'
            )
            return self
        cache_dir = (
            plb.Path(user_cache_dir('persona', 'jasper_ginn', ensure_exists=True)) / 'duckdb'
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._logger.debug(f'Using DuckDB cache directory at: {str(cache_dir)}')
        self._conn = duckdb.connect(database=':memory:persona')
        self._conn.execute(
            'INSTALL httpfs; LOAD httpfs; INSTALL cache_httpfs FROM community; LOAD cache_httpfs;'
        )
        self._conn.execute(
            f"SET cache_httpfs_cache_directory = '{str(cache_dir)}'; SET cache_httpfs_type = 'on_disk';"
        )
        self._conn.execute(
            'SET cache_httpfs_enable_cache_validation = true;'
        )  # this checks for updated files on read
        return self

    def close(self):
        if self._conn is not None:
            self._logger.debug('Closing DuckDB connection ...')
            if not self._read_only:
                # NB: dump tables to storage
                self._export_tables()
            self._conn.close()
            self._conn = None

    def get_cursor(self) -> CursorLike:
        if self._conn is None:
            raise RuntimeError('No database connection; call connect() first.')
        return self._conn.cursor()
