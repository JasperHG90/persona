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
    def __init__(self, config: DuckDBMetaStoreConfig, read_only: bool = True):
        super().__init__(config=config)

        self._conn: duckdb.DuckDBPyConnection | None = None
        self._logger.debug(
            f'Engine is in {"read only" if read_only else "write"} mode. Updates {"will not" if read_only else "will"} be persisted ...'
        )
        self._read_only = read_only

    def bootstrap(self):
        """Bootstraps the in-memory database using existing indexes if available."""
        if self._conn is None:
            raise RuntimeError('No database connection; call connect() first.')
        for table in ['roles', 'skills']:
            self._conn.execute(
                f'CREATE TABLE {table} (name VARCHAR PRIMARY KEY, description VARCHAR, uuid VARCHAR(32), files VARCHAR[], embedding FLOAT[384])'
            )
            path_ = getattr(self._config, f'{table}_index_path')
            try:
                self._logger.debug(f'Loading existing {table} index from disk ...')
                self._conn.execute(f"INSERT INTO {table} SELECT * FROM read_parquet('{path_}');")
            except Exception:
                self._logger.warning(
                    f'No existing {table} index found at {path_}: Table initialized empty ...'
                )
        return self

    def _export_tables(self):
        """Exports the in-memory database tables to disk."""
        if self._conn is None:
            raise RuntimeError('No database connection; call connect() first.')
        for table in ['roles', 'skills']:
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


# class LanceDBMetaStore(MetaStore):
#     def __init__(
#         self,
#         uri: str,
#         storage_options: dict[str, str] | None = None,
#         client_config: ldb.ClientConfig | None = None,
#         optimize: bool = True,
#     ):
#         self.optimize = optimize
#         self._db = ldb.connect(
#             uri=uri,
#             storage_options=storage_options,
#             client_config=client_config,
#             session=global_session,
#         )
#         self._metadata: list[tuple[Literal['upsert', 'delete'], IndexEntry]] = []
#         self._transaction: Transaction | None = None
#         self._logger = logging.getLogger('persona.storage.base.VectorDatabase')

#     def get_or_create_table(self, table_name: Literal['personas', 'skills']) -> ldb.Table:
#         """Attempt to open an existing table, or create it if it doesn't exist."""
#         try:
#             table = self._db.open_table(name=table_name)
#         except ValueError:
#             func = get_registry().get('sentence-transformers').create()

#             # NB: this has some start-up time because it's loading the embedding model
#             class PersonaEmbedding(LanceModel):
#                 uuid: str
#                 name: str
#                 files: list[str]
#                 description: str = func.SourceField()
#                 vector: Vector(func.ndims()) = func.VectorField()  # type: ignore

#                 class Config:
#                     vector = 'embedding'
#                     embedding_function = func

#             table = self._db.create_table(name=table_name, schema=PersonaEmbedding)
#         return table

#     def update_table(
#         self, table_name: Literal['personas', 'skills'], data: list[dict[str, str | list[str]]]
#     ):
#         """Update the index table with new data. Existing entries will be updated."""
#         table = self.get_or_create_table(table_name)
#         (
#             table.merge_insert('name')
#             .when_matched_update_all()
#             .when_not_matched_insert_all()
#             .execute(new_data=data)
#         )
#         if self.optimize:
#             table.optimize()

#     def create_persona_tables(self):
#         """Create the persona and skills tables if they don't exist."""
#         self.get_or_create_table('personas')
#         self.get_or_create_table('skills')

#     def drop_all_tables(self) -> None:
#         """Drop the entire database."""
#         self._db.drop_all_tables()

#     def remove(self, table_name: Literal['personas', 'skills'], names: list[str]) -> None:
#         """Remove entries from the specified table by name."""
#         table = self.get_or_create_table(table_name)
#         names_joined = ','.join([f"'{name}'" for name in names])
#         table.delete(where='name IN (%s)' % (names_joined))
#         if self.optimize:
#             table.optimize()

#     def exists(self, table_name: Literal['personas', 'skills'], name: str) -> bool:
#         """Check if an entry exists in the specified table by name."""
#         table = self.get_or_create_table(table_name)
#         n = table.count_rows(filter="name = '%s'" % (name))
#         return True if n > 0 else False

#     def get_record(
#         self, table_name: Literal['personas', 'skills'], name: str, filter: list[str] | None = None
#     ) -> dict[str, Any] | None:
#         """Get a record from the specified table by name."""
#         results = (
#             self.get_or_create_table(table_name).search().where("name = '%s'" % (name)).to_arrow()
#         )
#         if filter:
#             results = results.select(filter)
#         results = results.to_pylist()
#         if results:
#             return results[0]
#         return None

#     def search(
#         self,
#         query: str,
#         table_name: Literal['personas', 'skills'],
#         limit: int = 5,
#         max_cosine_distance: float | None = None,
#     ) -> LanceQueryBuilder:
#         """Search the specified table for the given query."""
#         return (
#             self.get_or_create_table(table_name)
#             .search(query)
#             .distance_type('cosine')  # type: ignore
#             .distance_range(upper_bound=max_cosine_distance)
#             .limit(limit)
#         )

#     def index(self, entry: IndexEntry) -> None:
#         """Stage metadata to be written to the metastore"""
#         if self._transaction:
#             self._metadata.append(('upsert', entry))
#         else:
#             self._logger.warning('Attempted to index entry outside of transaction.')

#     def deindex(self, entry: IndexEntry) -> None:
#         """Stage metadata deletion from the metastore"""
#         if self._transaction:
#             self._metadata.append(('delete', entry))
#         else:
#             self._logger.warning('Attempted to deindex entry outside of transaction.')
