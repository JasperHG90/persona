from unittest.mock import MagicMock
from persona.mcp.models import AppContext, TemplateSummary, TemplateDetails
from persona.storage.base import StorageBackend, VectorDatabase
from persona.config import StorageConfig


def test_app_context_initialization():
    """Test that AppContext can be initialized with a StorageConfig."""
    mock_storage_config = MagicMock(spec=StorageConfig)
    mock_storage_backend = MagicMock(spec=StorageBackend)
    mock_vector_db = MagicMock(spec=VectorDatabase)
    app_context = AppContext(config=mock_storage_config)
    app_context._target_storage = mock_storage_backend
    app_context._vector_db = mock_vector_db
    assert app_context.config is mock_storage_config
    assert app_context._target_storage is mock_storage_backend
    assert app_context._vector_db is mock_vector_db


def test_template_summary_initialization():
    """Test that TemplateSummary can be initialized with name, description, and uuid."""
    summary = TemplateSummary(name='test', description='a test', uuid='1234')
    assert summary.name == 'test'
    assert summary.description == 'a test'
    assert summary.uuid == '1234'


def test_template_details_initialization():
    """Test that TemplateDetails can be initialized with name, description, and prompt."""
    details = TemplateDetails(name='test', description='a test', prompt='a prompt')
    assert details.name == 'test'
    assert details.description == 'a test'
    assert details.prompt == 'a prompt'
