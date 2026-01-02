import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from persona.mcp.server import (
    AppContext,
    _list,
    _get_persona,
)
from persona.config import StorageConfig


def side_effect_get_or_create_table(table_name: str):
    if table_name == 'skills':
        mock_table = MagicMock()
        mock_table.to_arrow.return_value.select.return_value.to_pylist.return_value = [
            {'name': 'fakedescription', 'description': 'A fake skill', 'uuid': 'abcd'},
            {'name': 'another_skill', 'description': 'Another skill', 'uuid': 'efgh'},
        ]
        return mock_table
    elif table_name == 'personas':
        mock_table = MagicMock()
        mock_table.to_arrow.return_value.select.return_value.to_pylist.return_value = [
            {'name': 'test_persona', 'description': 'a test', 'uuid': '1234'},
        ]
        return mock_table


@pytest_asyncio.fixture
async def mock_app_context():
    # Mock the AppContext index
    mock_vector_db = MagicMock()
    mock_vector_db._metadata = []
    get_or_create_table_mock = MagicMock(side_effect=side_effect_get_or_create_table)
    mock_vector_db.get_or_create_table.side_effect = get_or_create_table_mock

    mock_storage_config = StorageConfig.model_validate(
        {'type': 'local', 'root': '/tmp/test_persona'}
    )
    app_context = AppContext(config=mock_storage_config)
    app_context._vector_db = mock_vector_db
    app_context._target_storage = MagicMock()
    # a string containing valid yaml frontmatter
    app_context._target_storage.load.return_value = """---
name: test
description: a test
---
some content
""".encode('utf-8')
    return app_context


@pytest.mark.asyncio
async def test_list_skills_logic(mock_app_context):
    response = await _list('skills', mock_app_context)
    assert len(response) == 2
    assert response[0]['name'] == 'fakedescription'
    assert response[1]['name'] == 'another_skill'


@pytest.mark.asyncio
async def test_list_personas_logic(mock_app_context):
    response = await _list('personas', mock_app_context)
    assert len(response) == 1
    assert response[0]['name'] == 'test_persona'


@pytest.mark.asyncio
async def test_get_persona_logic(mock_app_context):
    response = await _get_persona(mock_app_context, 'test_persona')
    assert response.name == 'test_persona'
