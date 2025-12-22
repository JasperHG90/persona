import pytest

from persona.storage import VectorDatabase


@pytest.fixture(scope="function")
def vector_db(tmp_path_factory: pytest.TempPathFactory) -> VectorDatabase:
    temp_dir = tmp_path_factory.mktemp("vector_db")
    vector_db = VectorDatabase(uri=str(temp_dir))
    vector_db.drop_all_tables()
    vector_db.create_persona_tables()
    return vector_db
