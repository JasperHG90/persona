import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastmcp import Context
from persona.mcp.server import (
    list_roles,
    list_skills,
    install_skill,
    get_skill_version,
    get_role,
    match_role,
    match_skill,
    persona_roleplay,
    persona_template,
    persona_review,
    persona_edit,
    skill_deploy,
    skill_update,
)
from persona.mcp.models import TemplateDetails
from persona.models import TemplateMatch
from persona.api import PersonaAPI


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock(spec=Context)


@pytest.fixture
def mock_api() -> MagicMock:
    return MagicMock(spec=PersonaAPI)


def test_list_roles(mock_context: MagicMock, mock_api: MagicMock) -> None:
    mock_api.list_templates.return_value = [{'name': 'role1', 'description': 'desc', 'uuid': '123'}]

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = list_roles.fn(mock_context)

    mock_api.list_templates.assert_called_once_with(
        'roles', columns=['name', 'description', 'uuid']
    )
    assert result == [{'name': 'role1', 'description': 'desc', 'uuid': '123'}]


def test_list_skills(mock_context: MagicMock, mock_api: MagicMock) -> None:
    mock_api.list_templates.return_value = [
        {'name': 'skill1', 'description': 'desc', 'uuid': '456'}
    ]

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = list_skills.fn(mock_context)

    mock_api.list_templates.assert_called_once_with(
        'skills', columns=['name', 'description', 'uuid']
    )
    assert result == [{'name': 'skill1', 'description': 'desc', 'uuid': '456'}]


def test_install_skill(mock_context: MagicMock, mock_api: MagicMock) -> None:
    mock_api.install_skill.return_value = '/path/to/SKILL.md'

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = install_skill.fn(mock_context, name='skill1', local_skill_dir='/tmp/skills')

    # Check that it converted string to Path
    mock_api.install_skill.assert_called_once()
    args, _ = mock_api.install_skill.call_args
    assert args[0] == 'skill1'
    assert str(args[1]) == '/tmp/skills'
    assert result == '/path/to/SKILL.md'


def test_get_skill_version(mock_context: MagicMock, mock_api: MagicMock) -> None:
    mock_api.get_skill_version.return_value = 'v1.0'

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = get_skill_version.fn(mock_context, name='skill1')

    mock_api.get_skill_version.assert_called_once_with('skill1')
    assert result == 'v1.0'


def test_get_role(mock_context: MagicMock, mock_api: MagicMock) -> None:
    # returns raw bytes of frontmatter
    raw_content = b"""---
description: A test role
---
You are a test role.
"""
    mock_api.get_definition.return_value = raw_content

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = get_role.fn(mock_context, name='test_role')

    mock_api.get_definition.assert_called_once_with('test_role', 'roles')
    assert isinstance(result, TemplateDetails)
    assert result.name == 'test_role'
    assert result.description == 'A test role'
    assert result.prompt == 'You are a test role.'


def test_match_role(mock_context: MagicMock, mock_api: MagicMock) -> None:
    search_results = [{'name': 'match1', 'description': 'desc', 'uuid': '111', 'score': 0.9}]
    mock_api.search_templates.return_value = search_results

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = match_role.fn(mock_context, query='expert', limit=5, max_cosine_distance=0.5)

    mock_api.search_templates.assert_called_once_with(
        query='expert',
        type='roles',
        columns=['name', 'description', 'uuid'],
        limit=5,
        max_cosine_distance=0.5,
    )
    assert len(result) == 1
    assert isinstance(result[0], TemplateMatch)
    assert result[0].name == 'match1'


def test_match_skill(mock_context: MagicMock, mock_api: MagicMock) -> None:
    search_results = [{'name': 'skill1', 'description': 'desc', 'uuid': '222', 'score': 0.8}]
    mock_api.search_templates.return_value = search_results

    with patch('persona.mcp.server.get_api', return_value=mock_api):
        result = match_skill.fn(mock_context, query='tool', limit=3, max_cosine_distance=0.4)

    mock_api.search_templates.assert_called_once_with(
        query='tool',
        type='skills',
        columns=['name', 'description', 'uuid'],
        limit=3,
        max_cosine_distance=0.4,
    )
    assert len(result) == 1
    assert isinstance(result[0], TemplateMatch)
    assert result[0].name == 'skill1'


# Async prompt tests
# We mock aiofiles.open to return a mock object that supports async read


@pytest.mark.asyncio
async def test_persona_roleplay() -> None:
    mock_file = AsyncMock()
    mock_file.read.return_value = 'Template content'
    mock_open = MagicMock()
    mock_open.__aenter__.return_value = mock_file

    with patch('aiofiles.open', return_value=mock_open):
        result = await persona_roleplay.fn('my description')

    assert 'Template content' in result
    assert 'my description' in result


@pytest.mark.asyncio
async def test_persona_template() -> None:
    mock_file = AsyncMock()
    mock_file.read.return_value = 'Template content'
    mock_open = MagicMock()
    mock_open.__aenter__.return_value = mock_file

    with patch('aiofiles.open', return_value=mock_open):
        result = await persona_template.fn('my description')

    assert 'Template content' in result
    assert 'my description' in result


@pytest.mark.asyncio
async def test_persona_review() -> None:
    mock_file = AsyncMock()
    mock_file.read.return_value = 'Review template'
    mock_open = MagicMock()
    mock_open.__aenter__.return_value = mock_file

    with patch('aiofiles.open', return_value=mock_open):
        result = await persona_review.fn('role def', chat_history='history')

    assert 'Review template' in result
    assert 'role def' in result
    assert 'history' in result


@pytest.mark.asyncio
async def test_persona_edit() -> None:
    mock_file = AsyncMock()
    mock_file.read.return_value = 'Edit template'
    mock_open = MagicMock()
    mock_open.__aenter__.return_value = mock_file

    with patch('aiofiles.open', return_value=mock_open):
        result = await persona_edit.fn('role def', feedback='bad')

    assert 'Edit template' in result
    assert 'role def' in result
    assert 'bad' in result


@pytest.mark.asyncio
async def test_skill_deploy() -> None:
    mock_file = AsyncMock()
    mock_file.read.return_value = 'Deploy template'
    mock_open = MagicMock()
    mock_open.__aenter__.return_value = mock_file

    with patch('aiofiles.open', return_value=mock_open):
        result = await skill_deploy.fn('do task')

    assert 'Deploy template' in result
    assert 'do task' in result


@pytest.mark.asyncio
async def test_skill_update() -> None:
    mock_file = AsyncMock()
    mock_file.read.return_value = 'Update template'
    mock_open = MagicMock()
    mock_open.__aenter__.return_value = mock_file

    with patch('aiofiles.open', return_value=mock_open):
        result = await skill_update.fn('my_skill')

    assert 'Update template' in result
    assert 'my_skill' in result
