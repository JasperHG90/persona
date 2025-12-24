from typing import cast, BinaryIO
from unittest.mock import patch, MagicMock

import pytest
from persona.storage.base import (
    TemplateHashValues,
    Transaction,
    StorageBackend,
    VectorDatabase,
)
from fsspec.implementations.memory import MemoryFileSystem

from persona.storage.models import IndexEntry


class TestTemplateHashValues:
    def test_hash_content(self):
        # Arrange
        thv = TemplateHashValues()
        content = b'hello world'

        # Act
        hashed_content = thv._hash_content(content)

        # Assert
        assert hashed_content == '5eb63bbbe01eeed093cb22bb8f5acdc3'

    def test_add(self):
        # Arrange
        thv = TemplateHashValues()

        # Act
        thv.add('file.txt', b'hello world')

        # Assert
        assert 'file.txt' in thv.root
        assert thv.root['file.txt'] == '5eb63bbbe01eeed093cb22bb8f5acdc3'

    def test_hash(self):
        # Arrange
        thv = TemplateHashValues()
        thv.add('file1.txt', b'content1')
        thv.add('file2.txt', b'content2')

        # Act
        h = thv.hash()

        # Assert
        assert h == 'ecb041d7e358afd47b1aeafab30a7d3c'

    def test_hash_with_exclude(self):
        # Arrange
        thv = TemplateHashValues()
        thv.add('file1.txt', b'content1')
        thv.add('file2.txt', b'content2')

        # Act
        h = thv.hash(exclude={'file1.txt'})

        # Assert
        assert h == '1ca96cc295f6cd2c5b944a614f54e88b'


class MockStorageBackend(StorageBackend):
    def __init__(self, config):
        super().__init__(config)

    def initialize(self) -> MemoryFileSystem:
        return MemoryFileSystem()

    def _save(self, key: str, data: bytes) -> None:
        self._fs.pipe({self.join_path(key): data})

    def _delete(self, key: str, recursive: bool) -> None:
        if self.exists(key):
            self._fs.rm(self.join_path(key), recursive=recursive)

    def load(self, key: str) -> bytes:
        with cast(BinaryIO, self._fs.open(self.join_path(key), 'rb')) as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return self._fs.exists(self.join_path(key))


@pytest.fixture
def mock_storage_backend(tmp_path):
    from persona.config import LocalStorageConfig

    config = LocalStorageConfig(type='local', root=str(tmp_path))
    backend = MockStorageBackend(config)
    # Mock the internal logger to avoid real logging
    backend._logger = MagicMock()
    return backend


class TestStorageBackend:
    def test_join_path(self, mock_storage_backend):
        # Arrange
        key = 'test.txt'

        # Act
        path = mock_storage_backend.join_path(key)

        # Assert
        assert path == f'{mock_storage_backend.config.root}/test.txt'

    def test_save_and_load(self, mock_storage_backend):
        # Arrange
        key = 'test.txt'
        data = b'test data'

        # Act
        mock_storage_backend.save(key, data)
        loaded_data = mock_storage_backend.load(key)

        # Assert
        assert loaded_data == data

    def test_exists(self, mock_storage_backend):
        # Arrange
        key = 'test.txt'
        data = b'test data'
        mock_storage_backend.save(key, data)

        # Act & Assert
        assert mock_storage_backend.exists(key)
        assert not mock_storage_backend.exists('nonexistent.txt')

    def test_delete(self, mock_storage_backend):
        # Arrange
        key = 'test.txt'
        data = b'test data'
        mock_storage_backend.save(key, data)

        # Act
        mock_storage_backend.delete(key)

        # Assert
        assert not mock_storage_backend.exists(key)

    def test_save_in_transaction_new_file(self, mock_storage_backend):
        # Arrange
        key = 'new_file.txt'
        with Transaction(mock_storage_backend, MagicMock()) as t:
            # Act
            mock_storage_backend.save(key, b'new data')

            # Assert
            assert t._log[0] == ('delete', key, None)

    def test_save_in_transaction_existing_file(self, mock_storage_backend):
        # Arrange
        key = 'existing_file.txt'
        original_data = b'original data'
        mock_storage_backend.save(key, original_data)
        with Transaction(mock_storage_backend, MagicMock()) as t:
            # Act
            mock_storage_backend.save(key, b'updated data')

            # Assert
            assert t._log[0] == ('restore', key, original_data)

    def test_delete_in_transaction(self, mock_storage_backend):
        # Arrange
        key = 'delete_me.txt'
        original_data = b'some data'
        mock_storage_backend.save(key, original_data)
        with Transaction(mock_storage_backend, MagicMock()) as t:
            # Act
            mock_storage_backend.delete(key)
            # Assert
            assert t._log[0] == ('restore', key, original_data)

    def test_load_nonexistent_raises_error(self, mock_storage_backend):
        with pytest.raises(FileNotFoundError):
            mock_storage_backend.load('nonexistent.txt')


class TestTransaction:
    def test_transaction_context_manager(self, mock_storage_backend):
        # Act
        with Transaction(mock_storage_backend, MagicMock()) as t:
            # Assert
            assert mock_storage_backend._transaction is t
        assert mock_storage_backend._transaction is None

    def test_rollback_on_exception(self, mock_storage_backend):
        # Arrange
        key = 'test.txt'
        original_data = b'original data'
        mock_storage_backend.save(key, original_data)

        # Act & Assert
        with pytest.raises(ValueError):
            with Transaction(mock_storage_backend, MagicMock()):
                mock_storage_backend.save(key, b'new data')
                raise ValueError('Something went wrong')

        assert mock_storage_backend.load(key) == original_data

    def test_rollback_on_metadata_exception(self, mock_storage_backend):
        # Arrange
        key = 'test.txt'
        original_data = b'original data'
        mock_storage_backend.save(key, original_data)
        mock_vector_db = MagicMock()
        mock_vector_db._metadata = []

        # Act & Assert
        with pytest.raises(ValueError):
            with Transaction(mock_storage_backend, mock_vector_db) as t:
                mock_storage_backend.save(key, b'new data')
                # Force an error in metadata processing
                t._db._metadata.append(('upsert', IndexEntry(type='skill')))
                t._db._metadata.append(('upsert', IndexEntry(type='persona')))

        assert mock_storage_backend.load(key) == original_data

    def test_save_and_delete_within_transaction(self, mock_storage_backend):
        # Arrange
        key_to_save = 'save.txt'
        key_to_delete = 'delete.txt'
        mock_storage_backend.save(key_to_delete, b'delete me')

        # Act
        with Transaction(mock_storage_backend, MagicMock()) as t:
            mock_storage_backend.save(key_to_save, b'new file')
            mock_storage_backend.delete(key_to_delete)

            # Assert
            assert len(t._log) == 2
            assert t._log[0] == ('delete', key_to_save, None)
            assert t._log[1][0] == 'restore'
            assert t._log[1][1] == key_to_delete

    def test_transaction_id(self, mock_storage_backend):
        # Arrange
        with Transaction(mock_storage_backend, MagicMock()) as t:
            # Act
            mock_storage_backend.save('file1.txt', b'content1')
            mock_storage_backend.save('file2.txt', b'content2')

            # Assert
            assert t.transaction_id == 'ecb041d7e358afd47b1aeafab30a7d3c'


@pytest.fixture
def mock_vector_db():
    with patch('persona.storage.base.ldb.connect') as mock_connect:
        mock_db_instance = MagicMock()
        mock_connect.return_value = mock_db_instance
        db = VectorDatabase(uri='dummy_uri')
        db._db = mock_db_instance
        yield db


class TestVectorDatabase:
    def test_get_or_create_table_opens_existing(self, mock_vector_db):
        # Arrange
        mock_table = MagicMock()
        mock_vector_db._db.open_table.return_value = mock_table

        # Act
        table = mock_vector_db.get_or_create_table('personas')

        # Assert
        assert table == mock_table
        mock_vector_db._db.open_table.assert_called_once_with(name='personas')

    @patch('persona.storage.base.get_registry')
    def test_get_or_create_table_creates_new(self, mock_get_registry, mock_vector_db):
        # Arrange
        mock_vector_db._db.open_table.side_effect = ValueError
        mock_embedding_function = MagicMock()
        mock_embedding_function.create.return_value.ndims.return_value = 128
        mock_get_registry.return_value.get.return_value = mock_embedding_function

        # Act
        mock_vector_db.get_or_create_table('personas')

        # Assert
        mock_vector_db._db.create_table.assert_called_once()

    def test_update_table(self, mock_vector_db):
        # Arrange
        mock_table = MagicMock()
        mock_vector_db.get_or_create_table = MagicMock(return_value=mock_table)
        data = [{'name': 'test', 'description': 'description'}]

        # Act
        mock_vector_db.update_table('personas', data)

        # Assert
        mock_table.merge_insert.assert_called_once_with('name')

    def test_remove(self, mock_vector_db):
        # Arrange
        mock_table = MagicMock()
        mock_vector_db.get_or_create_table = MagicMock(return_value=mock_table)

        # Act
        mock_vector_db.remove('personas', ['test1', 'test2'])

        # Assert
        mock_table.delete.assert_called_once_with(where="name IN ('test1','test2')")

    def test_exists(self, mock_vector_db):
        # Arrange
        mock_table = MagicMock()
        mock_vector_db.get_or_create_table = MagicMock(return_value=mock_table)
        mock_table.count_rows.return_value = 1

        # Act & Assert
        assert mock_vector_db.exists('personas', 'test')
        mock_table.count_rows.return_value = 0
        assert not mock_vector_db.exists('personas', 'test')

    def test_get_record(self, mock_vector_db):
        # Arrange
        mock_table = MagicMock()
        mock_vector_db.get_or_create_table = MagicMock(return_value=mock_table)
        mock_arrow_table = MagicMock()
        mock_arrow_table.to_pylist.return_value = [{'name': 'test'}]
        mock_table.search.return_value.where.return_value.to_arrow.return_value = mock_arrow_table

        # Act
        record = mock_vector_db.get_record('personas', 'test')

        # Assert
        assert record == {'name': 'test'}

    def test_search(self, mock_vector_db):
        # Arrange
        mock_table = MagicMock()
        mock_vector_db.get_or_create_table = MagicMock(return_value=mock_table)
        mock_search = mock_table.search.return_value
        mock_distance_type = mock_search.distance_type
        mock_distance_range = mock_distance_type.return_value.distance_range
        mock_limit = mock_distance_range.return_value.limit

        # Act
        mock_vector_db.search('query', 'personas', limit=10, max_cosine_distance=0.5)

        # Assert
        mock_table.search.assert_called_once_with('query')
        mock_distance_type.assert_called_once_with('cosine')
        mock_distance_range.assert_called_once_with(upper_bound=0.5)
        mock_limit.assert_called_once_with(10)

    def test_index_and_deindex_with_transaction(self, mock_vector_db, mock_storage_backend):
        # Arrange
        with Transaction(mock_storage_backend, mock_vector_db) as t:
            entry = IndexEntry(name='test', type='skill')
            # Act
            mock_vector_db.index(entry)
            mock_vector_db.deindex(entry)
            # Assert
            assert t._db._metadata[0] == ('upsert', entry)
            assert t._db._metadata[1] == ('delete', entry)

    def test_index_and_deindex_outside_transaction(self, mock_vector_db, caplog):
        # Arrange
        entry = IndexEntry(name='test', type='skill')
        # Act
        mock_vector_db.index(entry)
        mock_vector_db.deindex(entry)
        # Assert
        assert 'Attempted to index entry outside of transaction.' in caplog.text
        assert 'Attempted to deindex entry outside of transaction.' in caplog.text
