from persona.storage.models import IndexEntry
from persona.storage.transaction import TemplateHashValues


class TestIndexEntry:
    def test_update(self) -> None:
        entry = IndexEntry(name='test', description='a test', uuid='123')
        entry.update('description', 'an updated test')
        assert entry.description == 'an updated test'

    def test_serialization_defaults(self) -> None:
        entry = IndexEntry()
        data = entry.model_dump()
        assert 'date_created' in data
        assert isinstance(data['date_created'], str)  # due to field_serializer

    def test_update_list(self) -> None:
        entry = IndexEntry(tags=['a'])
        entry.update('tags', ['a', 'b'])
        assert entry.tags == ['a', 'b']


class TestTemplateHashValues:
    def test_hash_content(self) -> None:
        thv = TemplateHashValues()
        content = b'hello world'
        # md5 of 'hello world' is 5eb63bbbe01eeed093cb22bb8f5acdc3
        assert thv._hash_content(content) == '5eb63bbbe01eeed093cb22bb8f5acdc3'

    def test_add(self) -> None:
        thv = TemplateHashValues()
        thv.add('file.txt', b'hello world')
        assert 'file.txt' in thv.root
        assert thv.root['file.txt'] == '5eb63bbbe01eeed093cb22bb8f5acdc3'

    def test_hash(self) -> None:
        thv = TemplateHashValues()
        thv.add('file1.txt', b'content1')
        thv.add('file2.txt', b'content2')

        # Hash depends on json dump of dict, sorted keys.
        # {"file1.txt": "...", "file2.txt": "..."}
        h = thv.hash()
        assert isinstance(h, str)
        assert len(h) == 32  # MD5 hex digest length

    def test_hash_with_exclude(self) -> None:
        thv = TemplateHashValues()
        thv.add('file1.txt', b'content1')
        thv.add('file2.txt', b'content2')

        h_full = thv.hash()
        h_excluded = thv.hash(exclude={'file1.txt'})

        assert h_full != h_excluded

        # Verify excluded hash matches hash of only file2
        thv2 = TemplateHashValues()
        thv2.add('file2.txt', b'content2')
        assert h_excluded == thv2.hash()
