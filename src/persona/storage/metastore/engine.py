"""
This module implements a bridge pattern for different metastore backends.
The Engine class can vary (e.g. DuckDB, Postgres, etc.), while the MetaStoreLogic
class provides the business logic for interacting with the metastore.
"""

import os
import logging
from typing import Generic, TypeVar, Generator, TYPE_CHECKING
import pathlib as plb
from abc import abstractmethod, ABCMeta
from contextlib import contextmanager

import duckdb
from platformdirs import user_data_dir, user_cache_dir

from persona.embedder import FastEmbedder, EmbeddingDownloader
from persona.config import BaseMetaStoreConfig, DuckDBMetaStoreConfig
from .utils import CursorLike

if TYPE_CHECKING:
    from .metastore import CursorLikeMetaStore

T = TypeVar('T', bound=BaseMetaStoreConfig)


class CursorLikeMetaStoreEngine(Generic[T], metaclass=ABCMeta):
    
    def __init__(self, config: T):
        self._logger = logging.getLogger(f"persona.storage.meta_store.{self.__class__.__name__}")
        self._config: T = config
    
    @abstractmethod
    def connect(self):
        ...
        
    @abstractmethod
    def close(self):
        ...
        
    @abstractmethod
    def get_cursor(self) -> CursorLike:
        ...
        
    @contextmanager
    def session(self) -> Generator[CursorLikeMetaStore, None, None]:
        self._logger.debug("Starting new metastore session ...")
        cursor = self.get_cursor()
        cursor.begin()
        try:
            yield CursorLikeMetaStore(cursor)
            cursor.commit()
        except Exception as e:
            self._logger.error(f"Session error: {e}. Rolling back transaction.")
            cursor.rollback()
            raise
        finally:
            self._logger.debug("Closing session ...")
            cursor.close()


class DuckDBMetaStoreEngine(CursorLikeMetaStoreEngine[DuckDBMetaStoreConfig]):
    
    def __init__(self, config: DuckDBMetaStoreConfig):
        super().__init__(config=config)
        
        model_dir = plb.Path(user_data_dir("persona", "jasper_ginn", ensure_exists=True)) / "embeddings/minilm-l6-v2-quantized"
        if not model_dir.exists():
            self._logger.info("Embedding model not found. Downloading...")
            downloader = EmbeddingDownloader()
            downloader.download()
        
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._model = FastEmbedder(model_dir=str(model_dir))
        
    def _bootstrap(self):
        """Bootstraps the in-memory database using existing on-disk database if available."""
        if self.conn is None:
            raise RuntimeError("No database connection; call connect() first.")
        index_path = self._config.index_path
        roles_path = os.path.join(index_path, "roles.parquet")
        skills_path = os.path.join(index_path, "skills.parquet")
        
        try:
            self._logger.debug("Loading existing index from disk ...")
            self.conn.execute(f"CREATE TABLE roles AS SELECT * FROM read_parquet('{roles_path}');")
            self.conn.execute(f"CREATE TABLE skills AS SELECT * FROM read_parquet('{skills_path}');")
        except Exception as e:
            self._logger.warning(f"Failed to load existing index: {e}")
            self.conn.execute("CREATE TABLE roles (name VARCHAR, description VARCHAR, uuid VARCHAR(32), files VARCHAR[], embedding FLOAT[384])")
            self.conn.execute("CREATE TABLE skills (name VARCHAR, description VARCHAR, uuid VARCHAR(32), embedding FLOAT[384])")

    def connect(self):
        cache_dir = plb.Path(user_cache_dir("persona", "jasper_ginn", ensure_exists=True)) / "duckdb"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._logger.debug(f"Using DuckDB cache directory at: {str(cache_dir)}")
        self.conn = duckdb.connect(database=":memory:persona", read_only=self._config.read_only)
        self.conn.execute("INSTALL httpfs; LOAD httpfs; INSTALL cache_httpfs FROM community; LOAD cache_httpfs;")
        self.conn.execute(f"SET cache_httpfs_cache_directory = '{str(cache_dir)}'; SET cache_httpfs_type = 'on_disk';")
        self.conn.execute("SET cache_httpfs_enable_cache_validation = true;") # this checks for updated files on read
        self._bootstrap()
        
    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            
    def get_cursor(self) -> CursorLike:
        if self.conn is None:
            raise RuntimeError("No database connection; call connect() first.")
        return self.conn.cursor()

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
