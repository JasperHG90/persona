import pytest
from unittest.mock import MagicMock, patch
from persona.config import PersonaConfig
from persona.api import PersonaAPI
from persona.tui.app import PersonaApp


@pytest.fixture
def mock_config():
    # Use a real object if possible to satisfy Pydantic/Type checks,
    # but here we can use a Mock that behaves like the config for the app's usage.
    # However, since PersonaApp types config, let's try to pass a real one or a compliant mock.
    # The directives advise real instances for simple data objects.
    # But PersonaConfig might have validation. Let's try a simple mock first,
    # matching the spec.
    config = MagicMock(spec=PersonaConfig)
    config.file_store = '/tmp/persona/files'
    config.meta_store = 'sqlite:///:memory:'
    config.root = '/tmp/persona'
    return config


@pytest.fixture
def mock_api():
    api = MagicMock(spec=PersonaAPI)
    # Default mocks for list/search
    api.list_templates.return_value = [
        {'name': 'Test Role', 'description': 'A test role', 'uuid': '123'},
        {'name': 'Another Role', 'description': 'Another one', 'uuid': '456'},
    ]
    api.search_templates.return_value = [
        {'name': 'Test Role', 'description': 'A test role', 'uuid': '123'},
    ]
    api.get_definition.return_value = b'---\nname: Test Role\n---\nSome content'

    # Mock _meta_store for on_unmount cleanup
    api._meta_store = MagicMock()
    api._meta_store.close = MagicMock()

    return api


@pytest.fixture
def mock_app(mock_config, mock_api):
    with (
        patch('persona.tui.app.get_meta_store_backend'),
        patch('persona.tui.app.get_file_store_backend'),
        patch('persona.tui.app.get_embedding_model'),
        patch('persona.tui.app.PersonaAPI', return_value=mock_api),
    ):
        app = PersonaApp(mock_config)
        # We also need to ensure app.api is our mock_api, though the patch above should handle initialization.
        # But just in case __init__ assigns it differently or we want direct access:
        app.api = mock_api
        yield app
