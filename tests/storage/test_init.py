import pytest
from persona.storage import get_storage_backend
from persona.storage.local import LocalStorageBackend
from persona.config import LocalStorageConfig, BaseStorageConfig


class TestGetStorageBackend:
    def test_get_local_storage_backend(self, tmp_path):
        # Arrange
        config = LocalStorageConfig(type='local', root=str(tmp_path))

        # Act
        backend = get_storage_backend(config)

        # Assert
        assert isinstance(backend, LocalStorageBackend)

    def test_get_storage_backend_invalid_config(self):
        # Arrange
        class InvalidStorageConfig(BaseStorageConfig):
            type: str = 'invalid'
            root: str = ''

        config = InvalidStorageConfig()

        # Act & Assert
        with pytest.raises(ValueError):
            get_storage_backend(config)
