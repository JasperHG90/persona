from persona.storage.models import IndexEntry


class TestIndexEntry:
    def test_update(self):
        # Arrange
        entry = IndexEntry(name='test', description='a test', uuid='123')

        # Act
        entry.update('description', 'an updated test')

        # Assert
        assert entry.description == 'an updated test'
