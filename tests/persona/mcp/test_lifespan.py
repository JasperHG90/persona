import pathlib as plb
from unittest.mock import MagicMock, patch
import pytest

from persona.mcp.utils.lifespan import lifespan, get_api
from persona.mcp.models import AppContext
from persona.config import PersonaConfig


@pytest.mark.asyncio
async def test_lifespan_minimal(tmp_path: plb.Path) -> None:
    # Arrange
    mock_server = MagicMock()

    # We need to mock a lot of stuff because lifespan calls them
    with (
        patch('persona.mcp.utils.lifespan.get_file_store_backend', return_value=MagicMock()),
        patch('persona.mcp.utils.lifespan.get_meta_store_backend', return_value=MagicMock()),
        patch('persona.mcp.utils.lifespan.get_embedding_model', return_value=MagicMock()),
        patch('persona.mcp.utils.lifespan.PersonaAPI', return_value=MagicMock()),
        patch(
            'persona.mcp.utils.lifespan.PersonaConfig.model_validate',
            return_value=MagicMock(model_dump=MagicMock(return_value={})),
        ),
        patch(
            'persona.mcp.utils.lifespan.parse_persona_config',
            return_value=MagicMock(spec=PersonaConfig),
        ),
    ):
        # Act
        async with lifespan(mock_server) as app_ctx:
            # Assert
            assert isinstance(app_ctx, AppContext)
            assert app_ctx._api is not None


def test_get_api() -> None:
    # Arrange
    mock_ctx = MagicMock()
    mock_app_ctx = MagicMock(spec=AppContext)
    mock_api = MagicMock()
    mock_app_ctx._api = mock_api

    # FastMCP Context structure: ctx.request_context.lifespan_context
    mock_ctx.request_context.lifespan_context = mock_app_ctx

    # Act
    api = get_api(mock_ctx)

    # Assert
    assert api == mock_api
