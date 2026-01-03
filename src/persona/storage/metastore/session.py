import logging
from abc import abstractmethod, ABCMeta

import pyarrow as pa

from persona.storage.metastore.utils import CursorLike


class BaseMetaStoreSession(metaclass=ABCMeta):
    def __init__(self, cursor: CursorLike):
        self._cursor = cursor
        self._logger = logging.getLogger(
            f'persona.storage.metastore.metastore.{self.__class__.__name__}'
        )

    @abstractmethod
    def upsert(self, table_name: str, data: list[dict[str, str | list[str]]]):
        """Insert or update a record

        Args:
            table_name (str): table in which to upsert the record. Should be one of persona.types.personaTypes
            data (list[dict[str, str  |  list[str]]]): either a single record or a list of records to upsert
        """
        ...

    @abstractmethod
    def truncate_tables(self):
        """Drops all tables in the metastore."""
        ...

    @abstractmethod
    def remove(self, table_name: str, keys: list[str]) -> None:
        """Deletes one or multiple records from the metastore

        Args:
            table_name (str): table from which to delete the records. Should be one of persona.types.personaTypes
            keys (list[str]): list of keys ('names') identifying the records to delete
        """
        ...

    @abstractmethod
    def exists(self, table_name: str, key: str) -> bool:
        """Checks if a records exists

        Args:
            table_name (str): table in which to check for existence. Should be one of persona.types.personaTypes
            key (str): key ('name' field) of the record to check for existence

        Returns:
            bool: _description_
        """
        ...

    @abstractmethod
    def get_one(
        self, table_name: str, key: str, column_filter: list[str] | None = None
    ) -> pa.Table:
        """Retrieve a single record

        Args:
            table_name (str): name of the table from which to retrieve the record. Should be one of persona.types.personaTypes
            key (str): key ('name' field) of the record to retrieve
            column_filter (list[str] | None, optional): list of columns to retrieve. Defaults to None.

        Returns:
            pa.Table: the retrieved record as a pyarrow Table
        """
        ...

    @abstractmethod
    def get_many(
        self,
        table_name: str,
        row_filter: list[str] | None = None,
        column_filter: list[str] | None = None,
    ) -> pa.Table:
        """Retrieve multiple records

        Args:
            table_name (str): name of the table from which to retrieve the records. Should be one of persona.types.personaTypes
            row_filter (list[str] | None, optional): list of keys ('name' fields) of the records to retrieve. Defaults to None.
            column_filter (list[str] | None, optional): list of columns to retrieve. Defaults to None.

        Returns:
            pa.Table: the retrieved records as a pyarrow Table
        """
        ...

    @abstractmethod
    def search(
        self,
        query: list[float],
        table_name: str,
        column_filter: list[str] | None = None,
        limit: int = 5,
        max_cosine_distance: float = 0.8,
    ) -> pa.Table:
        """Search for records based on a query embedding

        Args:
            query (list[float]): query embedding vector
            table_name (str): name of the table to search in. Should be one of persona.types.personaTypes
            limit (int, optional): maximum number of results to return. Defaults to 5.
            max_cosine_distance (float | None, optional): maximum cosine distance for filtering results. Defaults to None.

        Returns:
            pa.Table: the search results as a pyarrow Table
        """
        ...


class CursorLikeMetaStoreSession(BaseMetaStoreSession):
    @staticmethod
    def _get_column_filter(column_filter: list[str] | None) -> str:
        if column_filter is not None:
            columns = ', '.join([f'"{c}"' for c in column_filter])
        else:
            columns = '*'
        return columns

    def upsert(self, table_name: str, data: list[dict[str, str | list[str]]]):
        sql = f'INSERT OR REPLACE INTO "{table_name}" (name, date_created, description, tags, uuid, files, embedding) VALUES ($name, $date_created, $description, $tags, $uuid, $files, $embedding)'
        self._cursor.executemany(sql, data)

    def truncate_tables(self):
        sql = 'TRUNCATE roles; TRUNCATE skills;'
        self._cursor.execute(sql)

    def remove(self, table_name: str, keys: list[str]) -> None:
        sql = f'DELETE FROM "{table_name}" WHERE name = ANY(?)'
        self._cursor.execute(sql, [keys])

    def exists(self, table_name: str, key: str) -> bool:
        sql = f'SELECT 1 FROM "{table_name}" WHERE name = ? LIMIT 1'
        result = self._cursor.execute(sql, [key]).fetchone()
        return result is not None

    def get_one(
        self, table_name: str, key: str, column_filter: list[str] | None = None
    ) -> pa.Table:
        sql = f'SELECT {self._get_column_filter(column_filter)} FROM "{table_name}" WHERE name = ?'
        return self._cursor.execute(sql, [key]).fetch_arrow_table()

    def get_many(
        self,
        table_name: str,
        row_filter: list[str] | None = None,
        column_filter: list[str] | None = None,
    ) -> pa.Table:
        sql = f'SELECT {self._get_column_filter(column_filter)} FROM "{table_name}"'
        if row_filter is not None:
            sql += ' WHERE name = ANY(?)'
        return self._cursor.execute(
            sql, [] if row_filter is None else [row_filter]
        ).fetch_arrow_table()

    def search(
        self,
        query: list[float],
        table_name: str,
        column_filter: list[str] | None = None,
        limit: int = 5,
        max_cosine_distance: float = 0.8,
    ) -> pa.Table:
        columns = self._get_column_filter(column_filter)
        columns += ',ROUND(array_cosine_distance(embedding, ?::FLOAT[384])::DOUBLE, 3) as score'
        sql = f"""
        WITH search_results AS (
            SELECT {columns},
            FROM "{table_name}"
        )
        SELECT * FROM search_results
        """
        if max_cosine_distance is not None:
            sql += f'WHERE score <= {max_cosine_distance}'
        sql += f' ORDER BY score ASC LIMIT {limit}'
        return self._cursor.execute(sql, [query]).fetch_arrow_table()
