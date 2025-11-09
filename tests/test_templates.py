
import pathlib as plb
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from persona.storage.models import Index, IndexEntry, SubIndex
from persona.templates import Persona, Skill, TemplateFile


def test_template_path_validation_exists() -> None:
    with pytest.raises(ValidationError):
        Skill(path=plb.Path("non_existent_path"))


@pytest.mark.parametrize(
    ("file_name", "template_type"),
    [
        ("SKILL.md", Skill),
        ("PERSONA.md", Persona),
    ],
)
def test_template_file_template_name_correct_file(
    tmp_path: plb.Path, file_name: str, template_type
) -> None:
    template_file = tmp_path / file_name
    template_file.touch()
    template_type(path=template_file)


@pytest.mark.parametrize(
    ("file_name", "template_type"),
    [
        ("SKILL.md", Skill),
        ("PERSONA.md", Persona),
    ],
)
def test_template_file_template_name_correct_dir(
    tmp_path: plb.Path, file_name: str, template_type
) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / file_name).touch()
    template_type(path=template_dir)


def test_template_file_template_name_incorrect(tmp_path: plb.Path) -> None:
    template_file = tmp_path / "INVALID.md"
    template_file.touch()
    with pytest.raises(ValidationError):
        Skill(path=template_file)


def test_template_metadata_property(tmp_path: plb.Path) -> None:
    template_file = tmp_path / "SKILL.md"
    template_file.write_text("---\nname: test\ndescription: a test\n---\n")
    skill = Skill(path=template_file)
    assert skill.metadata == {"name": "test", "description": "a test"}


@pytest.mark.parametrize(
    ("template_class", "file_name", "is_dir"),
    [
        (Skill, "SKILL.md", False),
        (Persona, "PERSONA.md", True),
    ],
)
def test_template_copy_template(
    tmp_path: plb.Path, template_class, file_name: str, is_dir: bool
) -> None:
    # Arrange
    if is_dir:
        template_path = tmp_path / "template"
        template_path.mkdir()
        (template_path / file_name).write_text("---\n---\n")
    else:
        template_path = tmp_path / file_name
        template_path.write_text("---\n---\n")

    mock_storage = MagicMock()
    mock_storage.config.index = "index.json"
    mock_index = Index(skills=SubIndex(root={}), personas=SubIndex(root={}))
    mock_storage.load.return_value = mock_index.model_dump_json()

    entry = IndexEntry(name='test_name', description='test_description')
    template = template_class(path=template_path)

    # Act
    template.copy_template(entry, mock_storage)

    # Assert
    mock_storage.save.assert_called()

def test_template_copy_template_missing_name_description(tmp_path: plb.Path) -> None:
    template_file = tmp_path / "SKILL.md"
    template_file.write_text("---\n---\n")
    skill = Skill(path=template_file)
    mock_storage = MagicMock()
    entry = IndexEntry()
    with pytest.raises(ValueError):
        skill.copy_template(entry, mock_storage)

def test_template_copy_template_binary_file(tmp_path: plb.Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "SKILL.md").touch()
    binary_file = template_dir / "binary.bin"
    binary_file.write_bytes(b"\x80")

    mock_storage = MagicMock()
    mock_storage.config.index = "index.json"
    mock_storage.config.root = str(tmp_path)
    mock_index = Index(skills=SubIndex(root={}), personas=SubIndex(root={}))
    mock_storage.load.return_value = mock_index.model_dump_json()

    entry = IndexEntry(name='test_name', description='test_description')
    skill = Skill(path=template_dir)

    with patch('persona.templates.logger') as mock_logger:
        skill.copy_template(entry, mock_storage)
        mock_logger.warning.assert_called_with(
            f"Cannot read file {binary_file} as text, copying as binary."
        )

def test_skill_get_type(tmp_path: plb.Path) -> None:
    template_file = tmp_path / "SKILL.md"
    template_file.touch()
    skill = Skill(path=template_file)
    assert skill.get_type() == "skill"

def test_persona_get_type(tmp_path: plb.Path) -> None:
    template_file = tmp_path / "PERSONA.md"
    template_file.touch()
    persona = Persona(path=template_file)
    assert persona.get_type() == "persona"

def test_anytemplate_discriminator(tmp_path: plb.Path) -> None:
    skill_path = tmp_path / "SKILL.md"
    skill_path.touch()
    persona_path = tmp_path / "PERSONA.md"
    persona_path.touch()

    skill_data = {"type": "skill", "path": skill_path}
    persona_data = {"type": "persona", "path": persona_path}

    skill_obj = TemplateFile.validate_python(skill_data)
    persona_obj = TemplateFile.validate_python(persona_data)

    assert isinstance(skill_obj, Skill)
    assert isinstance(persona_obj, Persona)
