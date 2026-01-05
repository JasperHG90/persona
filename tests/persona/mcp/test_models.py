from unittest.mock import MagicMock
from persona.mcp.models import AppContext, TemplateDetails
from persona.config import PersonaConfig
from persona.storage import BaseFileStore, CursorLikeMetaStoreEngine
from persona.embedder import FastEmbedder
from persona.api import PersonaAPI


def test_app_context_initialization() -> None:
    """Test that AppContext can be initialized with required components."""
    # Use real config to avoid Pydantic validation issues with Mocks
    real_config = PersonaConfig(root='/tmp/test')

    mock_file_store = MagicMock(spec=BaseFileStore)
    mock_meta_store = MagicMock(spec=CursorLikeMetaStoreEngine)
    mock_embedder = MagicMock(spec=FastEmbedder)
    mock_api = MagicMock(spec=PersonaAPI)

    app_context = AppContext(config=real_config)

    # Private attributes are set after init in the lifespan
    app_context._file_store = mock_file_store
    app_context._meta_store_engine = mock_meta_store
    app_context._embedding_model = mock_embedder
    app_context._api = mock_api

    assert app_context.config is real_config
    assert app_context._file_store is mock_file_store
    assert app_context._meta_store_engine is mock_meta_store
    assert app_context._embedding_model is mock_embedder
    assert app_context._api is mock_api


def test_template_details_initialization() -> None:
    """Test that TemplateDetails can be initialized with name, description, and prompt."""
    details = TemplateDetails(name='test', description='a test', prompt='a prompt')
    assert details.name == 'test'
    assert details.description == 'a test'
    assert details.prompt == 'a prompt'
