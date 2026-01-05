from pathlib import Path
from unittest.mock import MagicMock

import pytest
from persona.config import LocalFileStoreConfig
from persona.storage.filestore import LocalFileStore
from persona.storage.transaction import Transaction


@pytest.fixture
def local_store(tmp_path: Path) -> LocalFileStore:
    config = LocalFileStoreConfig(root=str(tmp_path))
    return LocalFileStore(config)


def test_initialize(local_store: LocalFileStore) -> None:
    assert local_store._fs is not None


def test_join_path(local_store: LocalFileStore) -> None:
    key = 'foo/bar.txt'
    expected = f'{local_store.config.root}/{key}'
    assert local_store.join_path(key) == expected


def test_join_path_no_root() -> None:
    config = LocalFileStoreConfig(root='')
    store = LocalFileStore(config)
    with pytest.raises(ValueError, match='Root path is not set'):
        store.join_path('foo.txt')


def test_save_load(local_store: LocalFileStore) -> None:
    key = 'test.txt'
    data = b'hello world'
    local_store.save(key, data)
    assert local_store.load(key) == data


def test_exists(local_store: LocalFileStore) -> None:
    key = 'exists.txt'
    local_store.save(key, b'')
    assert local_store.exists(key)
    assert not local_store.exists('nonexistent.txt')


def test_delete(local_store: LocalFileStore) -> None:
    key = 'delete.txt'
    local_store.save(key, b'data')
    assert local_store.exists(key)
    local_store.delete(key)
    assert not local_store.exists(key)


def test_delete_recursive(local_store: LocalFileStore) -> None:
    local_store.save('dir/file1.txt', b'1')
    local_store.save('dir/file2.txt', b'2')
    assert local_store.is_dir('dir')
    local_store.delete('dir', recursive=True)
    assert not local_store.exists('dir')


def test_glob(local_store: LocalFileStore) -> None:
    local_store.save('glob/a.txt', b'')
    local_store.save('glob/b.txt', b'')
    results = local_store.glob('glob/*.txt')
    assert len(results) == 2
    assert any('a.txt' in r for r in results)
    assert any('b.txt' in r for r in results)


def test_save_with_transaction_new_file(local_store: LocalFileStore) -> None:
    mock_transaction = MagicMock(spec=Transaction)
    local_store._transaction = mock_transaction

    key = 'new.txt'
    data = b'content'
    local_store.save(key, data)

    # Should log 'delete' (rollback action for new file)
    mock_transaction._add_log_entry.assert_called_with('delete', key)
    mock_transaction._add_file_hash.assert_called_with(key, data)


def test_save_with_transaction_existing_file(local_store: LocalFileStore) -> None:
    key = 'update.txt'
    original_data = b'old'
    local_store.save(key, original_data)

    mock_transaction = MagicMock(spec=Transaction)
    local_store._transaction = mock_transaction

    new_data = b'new'
    local_store.save(key, new_data)

    # Should log 'restore' with original data
    mock_transaction._add_log_entry.assert_called_with('restore', key, original_data)
    mock_transaction._add_file_hash.assert_called_with(key, new_data)


def test_delete_with_transaction(local_store: LocalFileStore) -> None:
    key = 'del_trans.txt'
    data = b'data'
    local_store.save(key, data)

    mock_transaction = MagicMock(spec=Transaction)
    local_store._transaction = mock_transaction

    local_store.delete(key)

    # Should log 'restore' with original data
    mock_transaction._add_log_entry.assert_called_with('restore', key, data)
    mock_transaction._add_file_hash.assert_called_with(key, data)


def test_delete_dir_with_transaction_ignored(local_store: LocalFileStore) -> None:
    # Directories are not tracked in transaction rollback logic currently per code
    local_store.save('dir/file.txt', b'')

    mock_transaction = MagicMock(spec=Transaction)
    local_store._transaction = mock_transaction

    # Attempt to delete directory (should rely on underlying fs, no transaction logging logic for dirs in _delete wrapper?)
    # The code says: if not self._fs.isdir(self.join_path(key)): ... log ...
    local_store.delete('dir', recursive=True)

    mock_transaction._add_log_entry.assert_not_called()
