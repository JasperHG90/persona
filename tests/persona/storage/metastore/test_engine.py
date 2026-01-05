from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from persona.config import DuckDBMetaStoreConfig
from persona.storage.metastore.engine import DuckDBMetaStoreEngine


@pytest.fixture
def config(tmp_path: Path) -> DuckDBMetaStoreConfig:
    return DuckDBMetaStoreConfig(root=str(tmp_path))


@pytest.fixture
def engine(config: DuckDBMetaStoreConfig) -> DuckDBMetaStoreEngine:
    return DuckDBMetaStoreEngine(config)


def test_connect(engine: DuckDBMetaStoreEngine) -> None:
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        engine.connect()

        assert engine._conn == mock_conn
        # Verify extension loading calls
        mock_conn.execute.assert_any_call(
            'INSTALL httpfs; LOAD httpfs; INSTALL cache_httpfs FROM community; LOAD cache_httpfs;'
        )


def test_connect_idempotent(engine: DuckDBMetaStoreEngine) -> None:
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        engine.connect()
        engine.connect()  # Second call

        assert mock_connect.call_count == 1


def test_bootstrap(engine: DuckDBMetaStoreEngine) -> None:
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        engine.connect()

        engine.bootstrap()

        # Verify table creation
        calls = [c for c in mock_conn.execute.call_args_list if 'CREATE TABLE' in str(c)]
        assert len(calls) >= 2  # roles and skills
        assert any('roles' in str(c) for c in calls)
        assert any('skills' in str(c) for c in calls)


def test_close(engine: DuckDBMetaStoreEngine) -> None:
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        engine.connect()

        engine.close()

        assert engine._conn is None
        mock_conn.close.assert_called_once()


def test_close_read_write_exports(engine: DuckDBMetaStoreEngine) -> None:
    # Set engine to read-write
    engine._read_only = False

    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        engine.connect()

        engine.close()

        # Verify export
        export_calls = [c for c in mock_conn.execute.call_args_list if 'COPY' in str(c)]
        assert len(export_calls) >= 2  # Export for roles and skills


def test_session_context(engine: DuckDBMetaStoreEngine) -> None:
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        engine.connect()

        with engine.session():
            mock_cursor.begin.assert_called_once()

        mock_cursor.commit.assert_called_once()
        mock_cursor.close.assert_called_once()


def test_session_rollback_on_error(engine: DuckDBMetaStoreEngine) -> None:
    with patch('duckdb.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        engine.connect()

        with pytest.raises(ValueError):
            with engine.session():
                raise ValueError('error')

        mock_cursor.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
