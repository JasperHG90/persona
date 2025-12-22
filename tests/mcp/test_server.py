import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from persona.mcp.server import (
    AppContext,
    _list_skills_logic,
    _list_personas_logic,
    _get_skill_logic,
    _get_persona_logic,
)
from persona.storage.models import Index, SubIndex, IndexEntry
from fastmcp.exceptions import ToolError
from persona.config import StorageConfig


@pytest_asyncio.fixture
async def mock_app_context():
    # Mock the AppContext index
    mock_index = Index(
        personas=SubIndex(
            root={
                'test_persona': IndexEntry(
                    name='test_persona',
                    description='A test persona',
                    uuid='12345',
                )
            }
        ),
        skills=SubIndex(
            root={
                'fakedescription': IndexEntry(
                    name='fakedescription',
                    description='Some description of things',
                    uuid='0b35fcb04a7ac74a41271e2ced74fb62',
                ),
                'another_skill': IndexEntry(
                    name='another_skill',
                    description='Another test skill',
                    uuid='67890',
                ),
            }
        ),
    )

    mock_storage_config = StorageConfig.model_validate(
        {'type': 'local', 'root': '/tmp/test_persona'}
    )
    app_context = AppContext(config=mock_storage_config, index=mock_index)
    app_context._target_storage = MagicMock()
    # a string containing valid yaml frontmatter
    app_context._target_storage.load.return_value = """---
name: test
description: a test
---
some content
"""
    return app_context


@pytest.mark.asyncio
async def test_list_skills_logic(mock_app_context):
    response = await _list_skills_logic(mock_app_context)
    assert len(response) == 2
    assert response[0]['name'] == 'fakedescription'
    assert response[1]['name'] == 'another_skill'


@pytest.mark.asyncio
async def test_list_personas_logic(mock_app_context):
    response = await _list_personas_logic(mock_app_context)
    assert len(response) == 1
    assert response[0]['name'] == 'test_persona'


@pytest.mark.asyncio
async def test_get_skill_logic(mock_app_context):
    response = await _get_skill_logic(mock_app_context, 'fakedescription')
    assert response.name == 'fakedescription'


@pytest.mark.asyncio
async def test_get_persona_logic(mock_app_context):
    response = await _get_persona_logic(mock_app_context, 'test_persona')
    assert response.name == 'test_persona'


@pytest.mark.asyncio
async def test_get_nonexistent_skill_logic(mock_app_context):
    with pytest.raises(ToolError, match='Skill not found'):
        await _get_skill_logic(mock_app_context, 'nonexistent_skill')


@pytest.mark.asyncio
async def test_get_nonexistent_persona_logic(mock_app_context):
    with pytest.raises(ToolError, match='Persona not found'):
        await _get_persona_logic(mock_app_context, 'nonexistent_persona')
