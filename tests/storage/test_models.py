import pytest
from persona.storage.models import IndexEntry, SubIndex, Index


class TestIndexEntry:
    def test_update(self):
        # Arrange
        entry = IndexEntry(name='test', description='a test', uuid='123')

        # Act
        entry.update('description', 'an updated test')

        # Assert
        assert entry.description == 'an updated test'


class TestSubIndex:
    def test_exists(self):
        # Arrange
        sub_index = SubIndex(root={'test': IndexEntry(name='test')})

        # Act & Assert
        assert sub_index.exists('test')
        assert not sub_index.exists('nonexistent')

    def test_upsert_new_entry(self):
        # Arrange
        sub_index = SubIndex(root={})
        entry = IndexEntry(name='new_entry')

        # Act
        sub_index.upsert(entry)

        # Assert
        assert 'new_entry' in sub_index.root
        assert sub_index.root['new_entry'] == entry

    def test_upsert_existing_entry(self):
        # Arrange
        existing_entry = IndexEntry(name='existing', description='original')
        sub_index = SubIndex(root={'existing': existing_entry})
        updated_entry = IndexEntry(name='existing', description='updated')

        # Act
        sub_index.upsert(updated_entry)

        # Assert
        assert sub_index.root['existing'].description == 'updated'

    def test_upsert_no_name(self):
        # Arrange
        sub_index = SubIndex(root={})
        entry = IndexEntry()

        # Act & Assert
        with pytest.raises(ValueError):
            sub_index.upsert(entry)

    def test_delete_existing(self):
        # Arrange
        sub_index = SubIndex(root={'to_delete': IndexEntry(name='to_delete')})

        # Act
        sub_index.delete('to_delete')

        # Assert
        assert 'to_delete' not in sub_index.root

    def test_delete_non_existing(self):
        # Arrange
        sub_index = SubIndex(root={})

        # Act
        sub_index.delete('nonexistent')

        # Assert
        # No error should be raised
        assert 'nonexistent' not in sub_index.root


class TestIndex:
    def test_instantiation(self):
        # Arrange
        personas = SubIndex(root={'p1': IndexEntry(name='p1')})
        skills = SubIndex(root={'s1': IndexEntry(name='s1')})

        # Act
        index = Index(personas=personas, skills=skills)

        # Assert
        assert index.personas == personas
        assert index.skills == skills
