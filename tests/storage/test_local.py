from unittest.mock import MagicMock

import pytest
from pathlib import Path
from fsspec.implementations.local import LocalFileSystem
from persona.storage.local import LocalStorageBackend
from persona.config import LocalStorageConfig
from persona.storage.base import Transaction


@pytest.fixture
def temp_storage_backend(tmp_path: Path) -> LocalStorageBackend:
    config = LocalStorageConfig(type='local', root=str(tmp_path))
    return LocalStorageBackend(config)


class TestLocalStorageBackend:
    def test_initialize(self, temp_storage_backend: LocalStorageBackend):
        # Act & Assert
        assert isinstance(temp_storage_backend.initialize(), LocalFileSystem)

    def test_join_path(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        key = 'test/file.txt'

        # Act
        path = temp_storage_backend.join_path(key)

        # Assert
        assert path == str(Path(temp_storage_backend.config.root) / key)

    def test_save_and_load(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        key = 'test.txt'
        data = b'hello world'

        # Act
        temp_storage_backend.save(key, data)
        loaded_data = temp_storage_backend.load(key)

        # Assert
        assert loaded_data == data

    def test_exists(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        key = 'test.txt'

        # Act & Assert
        assert not temp_storage_backend.exists(key)
        temp_storage_backend.save(key, b'data')
        assert temp_storage_backend.exists(key)

    def test_delete(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        key = 'test.txt'
        temp_storage_backend.save(key, b'data')

        # Act
        temp_storage_backend.delete(key)

        # Assert
        assert not temp_storage_backend.exists(key)

    def test_delete_recursive(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        dir_key = 'test_dir'
        file_key = f'{dir_key}/test.txt'
        temp_storage_backend.save(file_key, b'data')

        # Act
        temp_storage_backend.delete(dir_key, recursive=True)

        # Assert
        assert not temp_storage_backend.exists(dir_key)

    def test_save_with_transaction(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        key = 'transaction_save.txt'
        data = b'transaction data'

        # Act
        with Transaction(temp_storage_backend, MagicMock()):
            temp_storage_backend.save(key, data)

        # Assert
        assert temp_storage_backend.load(key) == data

    def test_delete_with_transaction(self, temp_storage_backend: LocalStorageBackend):
        # Arrange
        key = 'transaction_delete.txt'
        temp_storage_backend.save(key, b'data')

        # Act
        with Transaction(temp_storage_backend, MagicMock()):
            temp_storage_backend.delete(key)

        # Assert
        assert not temp_storage_backend.exists(key)
