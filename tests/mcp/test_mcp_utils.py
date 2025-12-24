import pathlib as plb
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Literal

import pytest
import frontmatter
from fastmcp.exceptions import ToolError

from persona.config import StorageConfig, LocalStorageConfig, BaseStorageConfig
from persona.mcp.models import AppContext, SkillFile
from persona.mcp.utils import (
    _get_builtin_skills,
    lifespan,
    _list,
    _write_skill_files,
    _get_skill_version,
    _skill_files,
    _get_skill,
    _get_persona,
    _match,
)


# Fixture for a mock AppContext
@pytest.fixture
def mock_app_context() -> AppContext:
    # Create a mock for BaseStorageConfig (which LocalStorageConfig inherits from)
    mock_base_storage_config = MagicMock(spec=BaseStorageConfig)
    mock_base_storage_config.index_path = "mock_index_path"
    mock_base_storage_config.root = "/mock/root/path"
    mock_base_storage_config.personas_dir = "/mock/root/path/personas"
    mock_base_storage_config.skills_dir = "/mock/root/path/skills"

    # Create a mock for LocalStorageConfig
    mock_local_storage_config = MagicMock(spec=LocalStorageConfig)
    mock_local_storage_config.type = "local"
    mock_local_storage_config.root = mock_base_storage_config.root # Ensure consistency
    mock_local_storage_config.index_path = mock_base_storage_config.index_path
    mock_local_storage_config.personas_dir = mock_base_storage_config.personas_dir
    mock_local_storage_config.skills_dir = mock_base_storage_config.skills_dir


    # Create a mock for StorageConfig, which wraps AnyStorage (LocalStorageConfig in this case)
    mock_storage_config = MagicMock(spec=StorageConfig)
    mock_storage_config.root = mock_local_storage_config # StorageConfig.root is the AnyStorage object

    mock_app_context = AppContext(config=mock_storage_config)
    mock_app_context._target_storage = MagicMock()
    mock_app_context._vector_db = MagicMock()
    return mock_app_context


# Test _get_builtin_skills
def test_get_builtin_skills_with_structure(tmp_path: plb.Path) -> None:
    # Arrange: Create a fake skill structure in tmp_path
    (tmp_path / "test_skill").mkdir(parents=True, exist_ok=True)
    (tmp_path / "test_skill" / "SKILL.md").write_text("content_skill_md")
    (tmp_path / "test_skill" / "script.py").write_text("content_script_py")
    (tmp_path / "another_skill").mkdir(parents=True, exist_ok=True)
    (tmp_path / "another_skill" / "SKILL.md").write_text("content_another_skill_md")

    with patch("persona.mcp.utils.library_skills_path", tmp_path):
        # Act: Call _get_builtin_skills
        skills = _get_builtin_skills()

        # Assert: Check if the returned dict is correct
        assert "test_skill" in skills
        assert "another_skill" in skills
        assert "SKILL.md" in skills["test_skill"]
        assert "script.py" in skills["test_skill"]
        assert skills["test_skill"]["SKILL.md"].content == b"content_skill_md"
        assert skills["test_skill"]["script.py"].content == b"content_script_py"
        assert skills["test_skill"]["SKILL.md"].extension == ".md"
        assert skills["test_skill"]["script.py"].extension == ".py"


# Test lifespan
@pytest.mark.asyncio
async def test_lifespan_from_config_file(tmp_path: plb.Path) -> None:
    # Arrange: Mock os.environ, Path.exists, open, yaml.safe_load, get_storage_backend, VectorDatabase
    mock_config_path = tmp_path / ".persona.config.yaml"
    mock_config_path.write_text("root:\n  index_path: /tmp/test_index")

    mock_config_data = {
        "type": "local",
        "root": str(tmp_path),
        "index": "test_index"
    }
    expected_storage_config = StorageConfig.model_validate(mock_config_data)

    with patch("persona.mcp.utils.os.environ", {"PERSONA_CONFIG_PATH": str(mock_config_path)}), \
         patch("persona.mcp.utils.plb.Path.exists", return_value=True), \
         patch("persona.mcp.utils.plb.Path.open", MagicMock(return_value=mock_config_path.open("r"))), \
         patch("persona.mcp.utils.yaml.safe_load", return_value=mock_config_data), \
         patch("persona.mcp.utils.get_storage_backend", return_value=MagicMock()), \
         patch("persona.mcp.utils.VectorDatabase", return_value=MagicMock()):
        # Act: Use the lifespan context manager
        async with lifespan(MagicMock()) as ctx:
            # Assert: Check if AppContext is created with correct config
            assert ctx.config.model_dump() == expected_storage_config.model_dump()
            assert ctx._target_storage is not None
            assert ctx._vector_db is not None


@pytest.mark.asyncio
async def test_lifespan_from_env_vars() -> None:
    # Arrange: Mock os.environ, Path.exists, parse_storage_config, get_storage_backend, VectorDatabase
    mock_storage_root_config = MagicMock(spec=LocalStorageConfig)
    mock_storage_root_config.type = "local"
    mock_storage_root_config.root = "/mock/env/root/path"
    mock_storage_root_config.index_path = "/mock/env/root/path/index"
    mock_storage_root_config.personas_dir = "/mock/env/root/path/personas"
    mock_storage_root_config.skills_dir = "/mock/env/root/path/skills"

    mock_storage_config = MagicMock(spec=StorageConfig)
    mock_storage_config.root = mock_storage_root_config

    with patch.dict("persona.mcp.utils.os.environ", {}, clear=True), \
         patch("persona.mcp.utils.plb.Path.exists", return_value=False), \
         patch("persona.mcp.utils.parse_storage_config", return_value=mock_storage_config), \
         patch("persona.mcp.utils.get_storage_backend", return_value=MagicMock()), \
         patch("persona.mcp.utils.VectorDatabase", return_value=MagicMock()):
        # Act: Use the lifespan context manager
        async with lifespan(MagicMock()) as ctx:
            # Assert: Check if AppContext is created with correct config
            assert ctx.config.root.index_path == "/mock/env/root/path/index"
            assert ctx._target_storage is not None
            assert ctx._vector_db is not None


# Test _list
@pytest.mark.asyncio
@pytest.mark.parametrize("list_type", ["personas", "skills"])
async def test_list_items(list_type: Literal["personas", "skills"], mock_app_context: AppContext) -> None:
    # Arrange: Mock AppContext and its VectorDatabase with a mock table
    mock_table = MagicMock()
    mock_table.to_arrow.return_value.select.return_value.to_pylist.return_value = [{"name": "test", "description": "desc", "uuid": "123"}]
    mock_app_context._vector_db.get_or_create_table.return_value = mock_table

    # Act: Call _list
    result = await _list(list_type, mock_app_context)

    # Assert: Check if the mock table's to_pylist was called
    mock_app_context._vector_db.get_or_create_table.assert_called_once_with(list_type)
    assert result == [{"name": "test", "description": "desc", "uuid": "123"}]


# Test _write_skill_files
@pytest.mark.asyncio
async def test_write_skill_files_not_absolute_path(mock_app_context: AppContext) -> None:
    # Arrange: Mock AppContext
    # Act & Assert: with pytest.raises(ToolError) call _write_skill_files with a relative path
    with pytest.raises(ToolError, match=r"Target skill directory \"relative/path\" is not an absolute path."):
        await _write_skill_files(mock_app_context, "relative/path", "test_skill")


@pytest.mark.asyncio
async def test_write_skill_files_dir_not_exists(mock_app_context: AppContext, tmp_path: plb.Path) -> None:
    # Arrange: Mock AppContext
    non_existent_path = tmp_path / "non_existent_dir"
    # Act & Assert: with pytest.raises(ToolError) call _write_skill_files for a non-existent path
    with pytest.raises(ToolError, match=r'Target skill directory ".*" does not exist\. Please create it before installing the skill\.'):
        await _write_skill_files(mock_app_context, str(non_existent_path), "test_skill")


@pytest.mark.asyncio
async def test_write_skill_files_builtin_skill(tmp_path: plb.Path, mock_app_context: AppContext) -> None:
    # Arrange: Patch library_skills with a mock skill
    mock_skill_files = {
        "SKILL.md": SkillFile(
            content=b"builtin skill content",
            name="SKILL.md",
            storage_file_path="skills/builtin_skill/SKILL.md",
            extension=".md",
        )
    }
    with patch("persona.mcp.utils.library_skills", {"builtin_skill": mock_skill_files}):
        # Act: Call _write_skill_files with an absolute path in tmp_path
        skill_file_path = await _write_skill_files(
            mock_app_context, str(tmp_path), "builtin_skill"
        )
        # Assert: Check if files were written correctly
        expected_path = tmp_path / "builtin_skill" / "SKILL.md"
        assert expected_path.exists()
        assert expected_path.read_bytes() == b"builtin skill content"
        assert skill_file_path == str(expected_path)


@pytest.mark.asyncio
async def test_write_skill_files_remote_skill(tmp_path: plb.Path, mock_app_context: AppContext) -> None:
    # Arrange: Mock _skill_files to return mock data
    mock_skill_files = {
        "SKILL.md": SkillFile(
            content=b"remote skill content",
            name="SKILL.md",
            storage_file_path="skills/remote_skill/SKILL.md",
            extension=".md",
        ),
        "script.py": SkillFile(
            content=b"remote script content",
            name="script.py",
            storage_file_path="skills/remote_skill/script.py",
            extension=".py",
        ),
    }
    with patch("persona.mcp.utils._skill_files", AsyncMock(return_value=mock_skill_files)):
        # Act: Call _write_skill_files
        skill_file_path = await _write_skill_files(
            mock_app_context, str(tmp_path), "remote_skill"
        )
        # Assert: Files are written
        expected_skill_md_path = tmp_path / "remote_skill" / "SKILL.md"
        expected_script_py_path = tmp_path / "remote_skill" / "script.py"
        assert expected_skill_md_path.exists()
        assert expected_skill_md_path.read_bytes() == b"remote skill content"
        assert expected_script_py_path.exists()
        assert expected_script_py_path.read_bytes() == b"remote script content"
        assert skill_file_path == str(expected_skill_md_path)


@pytest.mark.asyncio
async def test_write_skill_files_no_skill_md(tmp_path: plb.Path, mock_app_context: AppContext) -> None:
    # Arrange: Mock skill files but without SKILL.md
    mock_skill_files = {
        "script.py": SkillFile(
            content=b"script content",
            name="script.py",
            storage_file_path="skills/no_skill_md/script.py",
            extension=".py",
        )
    }
    with patch("persona.mcp.utils._skill_files", AsyncMock(return_value=mock_skill_files)):
        # Act & Assert: with pytest.raises(ToolError)
        with pytest.raises(ToolError, match=r'SKILL\.md file not found for skill ".*?"\. Installation may have failed\.'):
            await _write_skill_files(mock_app_context, str(tmp_path), "no_skill_md")


# Test _get_skill_version
@pytest.mark.asyncio
async def test_get_skill_version_exists(mock_app_context: AppContext) -> None:
    # Arrange: Mock AppContext and VectorDatabase to return a version
    mock_app_context._vector_db.exists.return_value = True
    mock_app_context._vector_db.get_record.return_value = {"uuid": "test_uuid"}

    # Act: Call _get_skill_version
    version = await _get_skill_version(mock_app_context, "test_skill")

    # Assert: Correct version is returned
    mock_app_context._vector_db.exists.assert_called_once_with("skills", "test_skill")
    mock_app_context._vector_db.get_record.assert_called_once_with(
        "skills", "test_skill", ["name", "files", "uuid"]
    )
    assert version == "test_uuid"


@pytest.mark.asyncio
async def test_get_skill_version_not_found(mock_app_context: AppContext) -> None:
    # Arrange: Mock VectorDatabase to show skill does not exist
    mock_app_context._vector_db.exists.return_value = False

    # Act & Assert: with pytest.raises(ToolError)
    with pytest.raises(ToolError, match="Skill \"test_skill\" not found"):
        await _get_skill_version(mock_app_context, "test_skill")


# Test _skill_files
@pytest.mark.asyncio
async def test_skill_files_found(mock_app_context: AppContext) -> None:
    # Arrange: Mock AppContext, VectorDatabase, and storage backend
    mock_app_context._vector_db.exists.return_value = True
    mock_app_context._vector_db.get_record.return_value = {
        "name": "test_skill",
        "files": ["skills/test_skill/SKILL.md", "skills/test_skill/script.py"],
        "uuid": "test_uuid",
    }

    original_loaded_content = b"skill md content"
    post_obj = frontmatter.loads(original_loaded_content)
    post_obj.metadata["version"] = "test_uuid"
    expected_skill_md_post = post_obj

    mock_app_context._target_storage.load.side_effect = [
        original_loaded_content,
        b"script content",
    ]

    # Act: Call _skill_files
    skill_files = await _skill_files(mock_app_context, "test_skill")

    # Assert: Returns correct dictionary of SkillFile objects
    actual_post = frontmatter.loads(skill_files["SKILL.md"].content)
    assert "SKILL.md" in skill_files
    assert "script.py" in skill_files
    assert actual_post.metadata == {"metadata": {"version": "test_uuid"}}
    assert actual_post.content == expected_skill_md_post.content
    assert skill_files["script.py"].content == b"script content"
    assert skill_files["SKILL.md"].extension == ".md"
    assert skill_files["script.py"].extension == ".py"


@pytest.mark.asyncio
async def test_skill_files_not_found(mock_app_context: AppContext) -> None:
    # Arrange: Mock VectorDatabase to show skill does not exist
    mock_app_context._vector_db.exists.return_value = False

    # Act & Assert: with pytest.raises(ToolError)
    with pytest.raises(ToolError, match="Skill \"test_skill\" not found"):
        await _skill_files(mock_app_context, "test_skill")


# Test _get_skill
@pytest.mark.asyncio
async def test_get_skill(mock_app_context: AppContext) -> None:
    # Arrange: Patch _skill_files to return a predefined dict
    mock_skill_files = {
        "SKILL.md": SkillFile(
            content=b"skill md content",
            name="SKILL.md",
            storage_file_path="skills/test_skill/SKILL.md",
            extension=".md",
        ),
        "script.py": SkillFile(
            content=b"script content",
            name="script.py",
            storage_file_path="skills/test_skill/script.py",
            extension=".py",
        ),
    }
    with patch("persona.mcp.utils._skill_files", AsyncMock(return_value=mock_skill_files)):
        # Act: Call _get_skill
        files = await _get_skill(mock_app_context, "test_skill")

        # Assert: Returns list of fastmcp File objects
        assert len(files) == 2
        assert files[0]._name == "SKILL.md"
        assert files[0].data == b"skill md content"
        assert files[1]._name == "script.py"
        assert files[1].data == b"script content"


# Test _get_persona
@pytest.mark.asyncio
async def test_get_persona_found(mock_app_context: AppContext) -> None:
    # Arrange: Mock AppContext, VectorDatabase, storage backend
    mock_app_context._vector_db.exists.return_value = True
    mock_app_context._target_storage.load.return_value = b"---\ndescription: Test Persona Description\n---\nTest Persona Prompt"

    # Act: Call _get_persona
    persona = await _get_persona(mock_app_context, "test_persona")

    # Assert: Returns correct TemplateDetails object
    assert persona.name == "test_persona"
    assert persona.description == "Test Persona Description"
    assert persona.prompt == "Test Persona Prompt"


@pytest.mark.asyncio
async def test_get_persona_not_found(mock_app_context: AppContext) -> None:
    # Arrange: Mock VectorDatabase to show persona does not exist
    mock_app_context._vector_db.exists.return_value = False

    # Act & Assert: with pytest.raises(ToolError)
    with pytest.raises(ToolError, match="Persona \"test_persona\" not found"):
        await _get_persona(mock_app_context, "test_persona")


# Test _match
@pytest.mark.asyncio
@pytest.mark.parametrize("match_type", ["personas", "skills"])
async def test_match_items(match_type: Literal["personas", "skills"], mock_app_context: AppContext) -> None:
    # Arrange: Mock AppContext and VectorDatabase.search
    mock_table = MagicMock()
    mock_table.to_arrow.return_value.select.return_value.to_pylist.return_value = [{"name": "match", "description": "desc", "uuid": "123", "_distance": 0.5}]
    mock_app_context._vector_db.search.return_value = mock_table

    # Act: Call _match
    result = await _match(match_type, "test query", mock_app_context, limit=1, max_cosine_distance=0.8)

    # Assert: Check if search was called with correct parameters
    mock_app_context._vector_db.search.assert_called_once_with(
        query="test query", table_name=match_type, limit=1, max_cosine_distance=0.8
    )
    assert result == [{"name": "match", "description": "desc", "uuid": "123", "_distance": 0.5}]