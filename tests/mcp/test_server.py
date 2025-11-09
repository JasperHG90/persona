import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from persona.mcp.server import (
    AppContext,
    _list_skills_logic,
    _list_personas_logic,
    _get_skill_logic,
    _get_persona_logic,
    _add_skill_logic,
    _add_persona_logic,
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
                    instructions='Be a test persona',
                    skills=['fakedescription'],
                )
            }
        ),
        skills=SubIndex(
            root={
                'fakedescription': IndexEntry(
                    name='fakedescription',
                    description='Some description of things',
                    uuid='0b35fcb04a7ac74a41271e2ced74fb62',
                    instructions='Describe things',
                    definition={'type': 'function', 'function': {'name': 'describe'}},
                ),
                'another_skill': IndexEntry(
                    name='another_skill',
                    description='Another test skill',
                    uuid='67890',
                    instructions='Do something else',
                    definition={'type': 'function', 'function': {'name': 'do_something_else'}},
                ),
            }
        ),
    )
    mock_storage_config = StorageConfig(root={'type': 'local', 'root': '/tmp/test_persona'})
    app_context = AppContext(config=mock_storage_config, index=mock_index)
    app_context._target_storage = MagicMock()
    return app_context


@pytest.mark.asyncio
async def test_list_skills_logic(mock_app_context):
    response = await _list_skills_logic(mock_app_context)
    assert len(response) == 2
    assert response[0].name == 'fakedescription'
    assert response[1].name == 'another_skill'


@pytest.mark.asyncio
async def test_list_personas_logic(mock_app_context):
    response = await _list_personas_logic(mock_app_context)
    assert len(response) == 1
    assert response[0].name == 'test_persona'


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


@pytest.mark.asyncio
async def test_add_skill_logic(mock_app_context):
    response = await _add_skill_logic(mock_app_context, 'new_skill', 'A new skill')
    assert response == "persona skill add --name new_skill --description 'A new skill'"


@pytest.mark.asyncio
async def test_add_persona_logic(mock_app_context):
    response = await _add_persona_logic(mock_app_context, 'new_persona', 'A new persona')
    assert response == "persona persona add --name new_persona --description 'A new persona'"
