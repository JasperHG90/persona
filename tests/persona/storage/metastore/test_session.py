import duckdb
import pytest
import pyarrow as pa
from typing import Generator
from persona.storage.metastore.session import CursorLikeMetaStoreSession


@pytest.fixture
def db_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    # Use real in-memory duckdb, skip extensions for test speed/reliability
    conn = duckdb.connect(':memory:')
    # Initialize schema manually since we aren't using the Engine's bootstrap which might try to load files
    conn.execute(
        'CREATE TABLE roles (name VARCHAR PRIMARY KEY, date_created TIMESTAMP, description VARCHAR, tags VARCHAR[], uuid VARCHAR(32), etag VARCHAR(32), files VARCHAR[], embedding FLOAT[384])'
    )
    conn.execute(
        'CREATE TABLE skills (name VARCHAR PRIMARY KEY, date_created TIMESTAMP, description VARCHAR, tags VARCHAR[], uuid VARCHAR(32), etag VARCHAR(32), files VARCHAR[], embedding FLOAT[384])'
    )
    yield conn
    conn.close()


@pytest.fixture
def session(db_connection: duckdb.DuckDBPyConnection) -> CursorLikeMetaStoreSession:
    cursor = db_connection.cursor()
    return CursorLikeMetaStoreSession(cursor)


def test_upsert_and_get_one(session: CursorLikeMetaStoreSession) -> None:
    data = [
        {
            'name': 'test-role',
            'date_created': '2023-01-01T00:00:00',
            'description': 'A test role',
            'tags': ['test'],
            'uuid': '123',
            'etag': 'abc',
            'files': ['ROLE.md'],
            'embedding': [0.1] * 384,
        }
    ]

    session.upsert('roles', data)

    result = session.get_one('roles', 'test-role')
    assert isinstance(result, pa.Table)
    assert len(result) == 1
    assert result.column('name')[0].as_py() == 'test-role'
    assert result.column('description')[0].as_py() == 'A test role'


def test_exists(session: CursorLikeMetaStoreSession) -> None:
    assert not session.exists('roles', 'nonexistent')

    data = [
        {
            'name': 'exists-role',
            'date_created': '2023-01-01T00:00:00',
            'description': 'desc',
            'tags': [],
            'uuid': '123',
            'etag': 'abc',
            'files': [],
            'embedding': None,
        }
    ]
    session.upsert('roles', data)

    assert session.exists('roles', 'exists-role')


def test_remove(session: CursorLikeMetaStoreSession) -> None:
    data = [
        {
            'name': 'delete-me',
            'date_created': '2023-01-01T00:00:00',
            'description': 'desc',
            'tags': [],
            'uuid': '123',
            'etag': 'abc',
            'files': [],
            'embedding': None,
        }
    ]
    session.upsert('roles', data)
    assert session.exists('roles', 'delete-me')

    session.remove('roles', ['delete-me'])
    assert not session.exists('roles', 'delete-me')


def test_get_many(session: CursorLikeMetaStoreSession) -> None:
    data = [
        {
            'name': 'role1',
            'date_created': '2023-01-01T00:00:00',
            'description': 'desc',
            'tags': [],
            'uuid': '1',
            'etag': 'a',
            'files': [],
            'embedding': None,
        },
        {
            'name': 'role2',
            'date_created': '2023-01-01T00:00:00',
            'description': 'desc',
            'tags': [],
            'uuid': '2',
            'etag': 'b',
            'files': [],
            'embedding': None,
        },
    ]
    session.upsert('roles', data)

    # Get all
    all_roles = session.get_many('roles')
    assert len(all_roles) == 2

    # Get specific
    some_roles = session.get_many('roles', row_filter=['role1'])
    assert len(some_roles) == 1
    assert some_roles.column('name')[0].as_py() == 'role1'


def test_truncate_tables(session: CursorLikeMetaStoreSession) -> None:
    data = [
        {
            'name': 'role1',
            'date_created': '2023-01-01T00:00:00',
            'description': 'desc',
            'tags': [],
            'uuid': '1',
            'etag': 'a',
            'files': [],
            'embedding': None,
        }
    ]
    session.upsert('roles', data)
    session.upsert('skills', data)

    session.truncate_tables()

    assert len(session.get_many('roles')) == 0
    assert len(session.get_many('skills')) == 0


def test_search(session: CursorLikeMetaStoreSession) -> None:
    # Vector search test
    # Embedding 1: all 1.0s
    emb1 = [1.0] * 384
    # Embedding 2: all 0.0s
    emb2 = [0.0] * 384

    data = [
        {
            'name': 'match',
            'date_created': '2023-01-01T00:00:00',
            'description': 'Should match',
            'tags': [],
            'uuid': '1',
            'etag': 'a',
            'files': [],
            'embedding': emb1,
        },
        {
            'name': 'no-match',
            'date_created': '2023-01-01T00:00:00',
            'description': 'Should not match',
            'tags': [],
            'uuid': '2',
            'etag': 'b',
            'files': [],
            'embedding': emb2,
        },
    ]
    session.upsert('roles', data)

    # Search for something close to emb1
    query = [0.9] * 384  # Close to 1.0, far from 0.0

    results = session.search(query, 'roles', limit=1)
    assert len(results) == 1
    assert results.column('name')[0].as_py() == 'match'
    assert 'score' in results.column_names
