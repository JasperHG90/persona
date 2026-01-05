import pytest
import pathlib as plb
from unittest.mock import MagicMock, patch
from persona.mcp.utils.lifespan import (
    lifespan,
    get_api,
    get_file_store,
    get_embedder,
    get_config,
    get_meta_store_session,
)
from persona.mcp.models import AppContext
from persona.config import PersonaConfig
from persona.api import PersonaAPI
from persona.storage import BaseFileStore, CursorLikeMetaStoreEngine
from persona.embedder import FastEmbedder
from fastmcp import Context


@pytest.mark.asyncio
async def test_lifespan_initialization(tmp_path: plb.Path) -> None:
    mock_server = MagicMock()

    # Mock PersonaConfig and its nested fields
    mock_persona_config = MagicMock(spec=PersonaConfig)

    mock_file_store_config = MagicMock()
    mock_file_store_config.root = '/tmp/root'
    mock_persona_config.file_store = mock_file_store_config

    mock_meta_store_config = MagicMock()
    mock_meta_store_config.root = '/tmp/root'
    mock_persona_config.meta_store = mock_meta_store_config

    # Need to handle the validator accessing these
    # The validator runs when model_validate is called on the real class,
    # but here we are patching model_validate to return our mock.
    # So `sync_root_paths` won't run on our mock unless we invoke it,
    # but the code calls `PersonaConfig.model_validate(config_raw)`.
    # Wait, the code calls `PersonaConfig.model_validate(config_raw)`.
    # Then `parse_persona_config` wraps it.

    mock_file_store = MagicMock(spec=BaseFileStore)
    mock_meta_store_engine = MagicMock(spec=CursorLikeMetaStoreEngine)
    mock_embedder = MagicMock(spec=FastEmbedder)
    mock_api = MagicMock(spec=PersonaAPI)

    # Mock chain for metastore: connect().bootstrap()
    mock_meta_store_engine.connect.return_value.bootstrap.return_value = mock_meta_store_engine

    with (
        patch('persona.mcp.utils.lifespan.os.environ.get', return_value=None),
        patch('persona.mcp.utils.lifespan.yaml.safe_load', return_value={}),
        patch(
            'persona.mcp.utils.lifespan.PersonaConfig.model_validate',
            return_value=MagicMock(model_dump=lambda: {}),
        ),
        patch('persona.mcp.utils.lifespan.parse_persona_config', return_value=mock_persona_config),
        patch('persona.mcp.utils.lifespan.get_file_store_backend', return_value=mock_file_store),
        patch(
            'persona.mcp.utils.lifespan.get_meta_store_backend', return_value=mock_meta_store_engine
        ),
        patch('persona.mcp.utils.lifespan.get_embedding_model', return_value=mock_embedder),
        patch('persona.mcp.utils.lifespan.PersonaAPI', return_value=mock_api),
    ):
        async with lifespan(mock_server) as app_ctx:
            assert isinstance(app_ctx, AppContext)
            assert app_ctx.config is mock_persona_config
            assert app_ctx._file_store is mock_file_store
            assert app_ctx._meta_store_engine is mock_meta_store_engine
            assert app_ctx._embedding_model is mock_embedder
            assert app_ctx._api is mock_api

            # Verify metastore closed on exit
            mock_meta_store_engine.close.assert_not_called()

        mock_meta_store_engine.close.assert_called_once()


def test_get_helpers() -> None:
    # Setup context
    mock_ctx = MagicMock(spec=Context)
    mock_request_context = MagicMock()
    mock_ctx.request_context = mock_request_context

    mock_app_context = MagicMock(spec=AppContext)
    mock_request_context.lifespan_context = mock_app_context

    # Setup app context attributes
    mock_api = MagicMock()
    mock_app_context._api = mock_api

    mock_file_store = MagicMock()
    mock_app_context._file_store = mock_file_store

    mock_embedder = MagicMock()
    mock_app_context._embedding_model = mock_embedder

    mock_config = MagicMock()
    mock_app_context.config = mock_config

    # Test getters
    assert get_api(mock_ctx) is mock_api
    assert get_file_store(mock_ctx) is mock_file_store
    assert get_embedder(mock_ctx) is mock_embedder
    assert get_config(mock_ctx) is mock_config


def test_get_meta_store_session() -> None:
    mock_ctx = MagicMock(spec=Context)
    mock_request_context = MagicMock()
    mock_ctx.request_context = mock_request_context

    mock_app_context = MagicMock(spec=AppContext)
    mock_request_context.lifespan_context = mock_app_context

    mock_engine = MagicMock()
    mock_app_context._meta_store_engine = mock_engine

    mock_session = MagicMock()
    mock_engine.read_session.return_value.__enter__.return_value = mock_session

    with get_meta_store_session(mock_ctx) as session:
        assert session is mock_session

    mock_engine.read_session.assert_called_once()
