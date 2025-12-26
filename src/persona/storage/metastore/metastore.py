import logging
from typing import Literal, TYPE_CHECKING
from abc import abstractmethod, ABCMeta

import pyarrow as pa

from persona.storage.models import IndexEntry

from .utils import CursorLike, personaTypes

if TYPE_CHECKING:
    from persona.storage.transaction import Transaction


class BaseMetaStore(metaclass=ABCMeta):
    
    def __init__(self, cursor: CursorLike):
        self._cursor = cursor
        self._logger = logging.getLogger(f"persona.storage.metastore.metastore.{self.__class__.__name__}")
        self._metadata: list[tuple[Literal['upsert', 'delete'], IndexEntry]] = []
        self._transaction: Transaction | None = None

    @abstractmethod
    def get_or_create_table(self, table_name: personaTypes):
        ...
        
    @abstractmethod
    def upsert(self, table_name: personaTypes, data: list[dict[str, str | list[str]]]):
        ...
        
    @abstractmethod
    def create_persona_tables(self):
        ...
        
    @abstractmethod
    def drop_all_tables(self):
        ...
        
    @abstractmethod
    def remove(self, table_name: personaTypes, keys: list[str]) -> None:
        ...
        
    @abstractmethod
    def exists(self) -> bool:
        ...
        
    @abstractmethod
    def get_one(self, table_name: personaTypes, key: str, column_filter: list[str] | None = None) -> pa.Table:
        ...
        
    @abstractmethod
    def get_many(self, table_name: personaTypes, row_filter: str | None = None, column_filter: list[str] | None = None) -> pa.Table:
        ...
        
    @abstractmethod
    def search(
        self,
        query: str,
        table_name: personaTypes,
        limit: int = 5,
        max_cosine_distance: float | None = None
    ) -> pa.Table:
        ...


class CursorLikeMetaStore(BaseMetaStore):
    
    def get_or_create_table(self, table_name: personaTypes):
        ...
        
    def upsert(self, table_name: personaTypes, data: list[dict[str, str | list[str]]]):
        ...
        
    def create_persona_tables(self):
        ...
        
    def drop_all_tables(self):
        ...
        
    def remove(self, table_name: personaTypes, keys: list[str]) -> None:
        ...
        
    def exists(self) -> bool:
        ...
        
    def get_one(self, table_name: personaTypes, key: str, column_filter: list[str] | None = None) -> pa.Table:
        ...
        
    def get_many(self, table_name: personaTypes, row_filter: str | None = None, column_filter: list[str] | None = None) -> pa.Table:
        ...
        
    def search(
        self,
        query: str,
        table_name: personaTypes,
        limit: int = 5,
        max_cosine_distance: float | None = None
    ) -> pa.Table:
        ...
