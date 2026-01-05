import pathlib as plb
from unittest.mock import MagicMock
import pytest

from persona.api import PersonaAPI
from persona.config import PersonaConfig


@pytest.fixture
def mock_config():
    config = MagicMock(spec=PersonaConfig)
    config.file_store = MagicMock()
    config.meta_store = MagicMock()
    config.meta_store.similarity_search.max_results = 5
    config.meta_store.similarity_search.max_cosine_distance = 0.5
    return config


@pytest.fixture
def api(mock_config):
    return PersonaAPI(
        config=mock_config, file_store=MagicMock(), meta_store=MagicMock(), embedder=MagicMock()
    )


def test_list_templates(api):
    # Arrange
    mock_session = MagicMock()
    api.meta_store.read_session.return_value.__enter__.return_value = mock_session
    mock_session.get_many.return_value.to_pylist.return_value = [
        {'name': 'test', 'description': 'desc', 'uuid': '123'}
    ]

    # Act
    results = api.list_templates('roles')

    # Assert
    assert len(results) == 1
    assert results[0].name == 'test'
    mock_session.get_many.assert_called_once_with(
        table_name='roles', column_filter=['name', 'description', 'uuid']
    )


def test_search_templates(api):
    # Arrange
    mock_session = MagicMock()
    api.meta_store.read_session.return_value.__enter__.return_value = mock_session
    api.embedder.encode.return_value = MagicMock(
        squeeze=MagicMock(return_value=MagicMock(tolist=MagicMock(return_value=[0.1, 0.2])))
    )
    mock_session.search.return_value.to_pylist.return_value = [
        {'name': 'test', 'description': 'desc', 'uuid': '123', 'score': 0.1}
    ]

    # Act
    results = api.search_templates('query', 'roles')

    # Assert
    assert len(results) == 1
    assert results[0].name == 'test'
    assert results[0].score == 0.1


def test_get_role(api):
    # Arrange
    mock_session = MagicMock()
    api.meta_store.read_session.return_value.__enter__.return_value = mock_session
    mock_session.exists.return_value = True
    api.file_store.load.return_value = b'---\ndescription: desc\n---\nprompt'

    # Act
    role = api.get_role('test_role')

    # Assert
    assert role.name == 'test_role'
    assert role.description == 'desc'
    assert role.prompt == 'prompt'


def test_install_skill(api, tmp_path):
    # Arrange
    mock_session = MagicMock()
    api.meta_store.read_session.return_value.__enter__.return_value = mock_session
    mock_session.exists.return_value = True
    mock_session.get_one.return_value.to_pylist.return_value = [
        {'name': 'test_skill', 'files': ['skills/test_skill/SKILL.md'], 'uuid': '123'}
    ]
    api.file_store.load.return_value = b'---\nname: test_skill\n---\ncontent'

    # Act
    skill_path = api.install_skill('test_skill', tmp_path)

    # Assert
    assert plb.Path(skill_path).exists()
    assert 'test_skill' in skill_path
