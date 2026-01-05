from unittest.mock import MagicMock, patch

import pytest
from persona.storage.filestore import BaseFileStore
from persona.storage.metastore import CursorLikeMetaStoreEngine, BaseMetaStoreSession
from persona.storage.models import IndexEntry
from persona.storage.transaction import Transaction


@pytest.fixture
def mock_file_store() -> MagicMock:
    fs = MagicMock(spec=BaseFileStore)
    fs._transaction = None
    return fs


@pytest.fixture
def mock_meta_store_engine() -> MagicMock:
    engine = MagicMock(spec=CursorLikeMetaStoreEngine)
    engine._transaction = None
    engine._metadata = []
    return engine


@pytest.fixture
def transaction(mock_file_store: MagicMock, mock_meta_store_engine: MagicMock) -> Transaction:
    return Transaction(mock_file_store, mock_meta_store_engine)


def test_context_manager(
    transaction: Transaction, mock_file_store: MagicMock, mock_meta_store_engine: MagicMock
) -> None:
    # WORKAROUND: Mock metadata so _process_metadata returns something, avoiding the early return bug in Transaction.__exit__
    # The bug is that if _process_metadata returns None, the cleanup code is skipped.
    # We verify the cleanup logic itself here by forcing a commit path.
    entry = IndexEntry(name='test', type='skill', files=['test/SKILL.md'])
    mock_meta_store_engine._metadata = [('upsert', entry)]

    # Also mock the session upsert so commit doesn't fail
    mock_connected = MagicMock()
    mock_session = MagicMock(spec=BaseMetaStoreSession)
    mock_meta_store_engine.open.return_value.__enter__.return_value = mock_connected
    mock_connected.session.return_value.__enter__.return_value = mock_session

    with patch('orjson.dumps', return_value=b'{}'):  # Mock dumps for manifest saving
        with transaction as t:
            assert t is transaction
            assert mock_file_store._transaction is t
            assert mock_meta_store_engine._transaction is t

    assert mock_file_store._transaction is None
    assert mock_meta_store_engine._transaction is None


def test_context_manager_empty_transaction_bug(
    transaction: Transaction, mock_file_store: MagicMock, mock_meta_store_engine: MagicMock
) -> None:
    # This test specifically targets the bug where an empty transaction (no metadata changes)
    # returns early in __exit__ and fails to clear the transaction references.
    with transaction:
        pass

    assert mock_file_store._transaction is None
    assert mock_meta_store_engine._transaction is None


def test_transaction_id(transaction: Transaction) -> None:
    # Initially empty hash
    # md5("{}") = 99914b932bd37a50b983c5e7c90ae93b
    assert transaction.transaction_id == '99914b932bd37a50b983c5e7c90ae93b'

    transaction._add_file_hash('file1', b'content1')
    tid1 = transaction.transaction_id

    transaction._add_file_hash('file2', b'content2')
    tid2 = transaction.transaction_id

    assert tid1 != tid2


def test_add_log_entry(transaction: Transaction) -> None:
    transaction._add_log_entry('restore', 'key1', b'data')
    assert len(transaction._log) == 1
    assert transaction._log[0] == ('restore', 'key1', b'data')


def test_rollback_explicit(transaction: Transaction, mock_file_store: MagicMock) -> None:
    # Setup log
    transaction._add_log_entry('restore', 'file1.txt', b'old_data')
    transaction._add_log_entry(
        'delete', 'file2.txt'
    )  # means we created file2, so rollback should delete it

    transaction.rollback()

    # Check calls in reverse order
    # 1. delete file2
    # 2. restore file1

    # We can check specific calls.
    # Note: rollback iterates reversed.
    # ('delete', 'file2.txt', None) -> _file_store._delete('file2.txt', recursive=False)
    # ('restore', 'file1.txt', b'old_data') -> _file_store._save('file1.txt', b'old_data')

    mock_file_store._delete.assert_called_with('file2.txt', recursive=False)
    mock_file_store._save.assert_called_with('file1.txt', b'old_data')


def test_process_metadata_upsert(
    transaction: Transaction, mock_meta_store_engine: MagicMock
) -> None:
    entry = IndexEntry(name='test', type='skill')
    mock_meta_store_engine._metadata = [('upsert', entry)]

    result = transaction._process_metadata()

    assert result is not None
    assert result['type'] == 'skill'
    assert len(result['upserts']) == 1
    assert result['upserts'][0]['name'] == 'test'
    assert result['deletes'] == []
    # Check UUID was assigned
    assert entry.uuid == transaction.transaction_id


def test_process_metadata_delete(
    transaction: Transaction, mock_meta_store_engine: MagicMock
) -> None:
    entry = IndexEntry(name='test', type='skill')
    mock_meta_store_engine._metadata = [('delete', entry)]

    result = transaction._process_metadata()

    assert result is not None
    assert result['type'] == 'skill'
    assert len(result['deletes']) == 1
    assert result['deletes'][0] == 'test'


def test_process_metadata_mixed_types_raises(
    transaction: Transaction, mock_meta_store_engine: MagicMock
) -> None:
    entry1 = IndexEntry(name='a', type='skill')
    entry2 = IndexEntry(name='b', type='role')
    mock_meta_store_engine._metadata = [('upsert', entry1), ('upsert', entry2)]

    with pytest.raises(ValueError, match='same type'):
        transaction._process_metadata()


def test_process_metadata_empty(transaction: Transaction) -> None:
    assert transaction._process_metadata() is None


@patch('orjson.dumps')
def test_commit_success(
    mock_dumps: MagicMock,
    transaction: Transaction,
    mock_meta_store_engine: MagicMock,
    mock_file_store: MagicMock,
) -> None:
    # Setup mock_dumps return value to be bytes
    mock_dumps.return_value = b'{"mock": "data"}'

    # Setup metadata
    entry = IndexEntry(name='test', type='skill', files=['test/SKILL.md'])
    mock_meta_store_engine._metadata = [('upsert', entry)]

    # Mock engine open/session
    mock_connected = MagicMock()
    mock_session = MagicMock(spec=BaseMetaStoreSession)
    mock_meta_store_engine.open.return_value.__enter__.return_value = mock_connected
    mock_connected.session.return_value.__enter__.return_value = mock_session

    with transaction:
        pass  # Trigger __exit__

    # Check manifest save
    mock_file_store.save.assert_called()  # Should save .manifest.json

    # Check index update
    mock_session.upsert.assert_called()


def test_commit_failure_exception_in_block(
    transaction: Transaction, mock_file_store: MagicMock
) -> None:
    transaction._add_log_entry('restore', 'file.txt', b'old')

    with pytest.raises(RuntimeError):
        with transaction:
            raise RuntimeError('Failure')

    # Check rollback happened
    mock_file_store._save.assert_called_with('file.txt', b'old')


def test_commit_failure_metadata_exception(
    transaction: Transaction, mock_meta_store_engine: MagicMock, mock_file_store: MagicMock
) -> None:
    # Setup metadata that causes error during process
    entry1 = IndexEntry(name='a', type='skill')
    entry2 = IndexEntry(name='b', type='role')  # Mixed types -> ValueError
    mock_meta_store_engine._metadata = [('upsert', entry1), ('upsert', entry2)]

    transaction._add_log_entry('restore', 'file.txt', b'old')

    with pytest.raises(ValueError):
        with transaction:
            pass

    # Check rollback happened
    mock_file_store._save.assert_called_with('file.txt', b'old')
