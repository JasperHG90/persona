"""Common-sense checks for the ONNX persona FT embeddings model."""

from typing import Generator
import pathlib as plb

import pytest
import duckdb
import numpy as np
from persona.embedder import FastEmbedder

embeddings_dir = plb.Path(__file__).parent.parent.parent.joinpath('scripts', 'embeddings')

if not embeddings_dir.joinpath('minilm-l6-v2-persona-ft-q8').exists():
    pytest.skip(
        'Embeddings not found. Please run the training script `scripts/embeddings/train.py` first. Skipping tests.',
        allow_module_level=True,
    )


@pytest.fixture(scope='module', autouse=True)
def conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create a DuckDB in-memory connection for testing."""
    connection = duckdb.connect(database=':memory:')
    yield connection
    connection.close()


@pytest.fixture(scope='module', autouse=True)
def tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create necessary tables for testing."""
    conn.execute("""
        CREATE TABLE docs (id INTEGER, content VARCHAR, embedding FLOAT[384]);
    """)
    conn.commit()


@pytest.fixture(scope='module', autouse=True)
def records() -> list[str]:
    return [
        'Machine Learning Engineer - The machine learning role is responsible for designing, building, and deploying machine learning models to solve real-world problems.',
        'Data Engineer - The data engineer role focuses on designing, building, and maintaining data pipelines and infrastructure to support data analytics and machine learning.',
        'Product Owner - The product owner role involves defining product vision, managing the product backlog, and ensuring the development team delivers value to the business.',
        'DevOps Engineer - The DevOps engineer role is responsible for automating and streamlining the software development and deployment processes, ensuring reliability and scalability of applications.',
    ]


@pytest.fixture(scope='module', autouse=True)
def embedder() -> FastEmbedder:
    return FastEmbedder(
        model_dir=str(embeddings_dir.joinpath('minilm-l6-v2-persona-ft-q8')),
        model_name='model.onnx',
    )


@pytest.fixture(scope='module', autouse=True)
def record_embeddings(
    embedder: FastEmbedder,
    records: list[str],
) -> np.ndarray[tuple[int, int], np.dtype[np.float32]]:
    embeddings = embedder.encode(records)
    return embeddings


@pytest.fixture(scope='module', autouse=True)
def insert_data(
    conn: duckdb.DuckDBPyConnection,
    tables: None,
    records: list[str],
    record_embeddings: np.ndarray[tuple[int, int], np.dtype[np.float32]],
) -> None:
    data = []
    for idx, (record, embedding) in enumerate(zip(records, record_embeddings)):
        data.append(
            {
                'id': idx,
                'content': record,
                'embedding': embedding.tolist(),
            }
        )
    conn.executemany(
        'INSERT INTO docs (id, content, embedding) VALUES ($id, $content, $embedding)',
        data,
    )
    conn.commit()


@pytest.mark.parametrize(
    'query,expected_ranking',
    [
        (
            'AI Specialist - The AI specialist role involves developing and implementing artificial intelligence solutions to enhance business processes and decision-making.',
            ['Machine Learning Engineer', 'Data Engineer', 'DevOps Engineer'],
        ),
        (
            'Analytics Engineer - The analytics engineer role focuses on building and maintaining data analytics infrastructure to support business intelligence and data-driven decision-making.',
            ['Data Engineer', 'DevOps Engineer', 'Machine Learning Engineer'],
        ),
        (
            'Scrum Master - The scrum master role is responsible for facilitating agile development processes, removing impediments, and ensuring effective communication within the development team.',
            ['DevOps Engineer', 'Product Owner', 'Machine Learning Engineer'],
        ),
        (
            'Cloud Engineer - The cloud engineer role involves designing, implementing, and managing cloud-based infrastructure and services to support scalable and reliable applications.',
            ['DevOps Engineer', 'Data Engineer', 'Machine Learning Engineer'],
        ),
    ],
)
def test_query(
    query: str, expected_ranking: list[str], conn: duckdb.DuckDBPyConnection, embedder: FastEmbedder
) -> None:
    sql = """
        SELECT id, content, ROUND(array_cosine_distance(embedding, ?::FLOAT[384]), 3) as score
        FROM docs
        WHERE score < 0.8
        ORDER BY score ASC
        LIMIT 3
    """
    vec = embedder.encode([query]).squeeze().tolist()
    res = conn.execute(sql, [vec]).fetch_arrow_table().to_pylist()
    rankings = [r['content'].split(' - ')[0] for r in res]
    assert len(rankings) == 3
    assert rankings == expected_ranking
