from typing import cast, BinaryIO

import pytest
from unittest.mock import MagicMock
from persona.storage.base import TemplateHashValues, Transaction, StorageBackend
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
