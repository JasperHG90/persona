import pathlib as plb
from unittest.mock import MagicMock

import numpy as np
import pytest
from pydantic import ValidationError

from persona.storage import IndexEntry
from persona.templates import (
    PersonaRootSourceFile,
    Role,
    Skill,
    SourceFile,
    TemplateFile,
    _is_persona_root_file,
)


@pytest.mark.parametrize(
    ('filename', 'expected'),
    [
        ('ROLE.md', True),
        ('SKILL.md', True),
        ('README.md', False),
        ('other.py', False),
    ],
)
def test_is_persona_root_file(filename: str, expected: bool) -> None:
    assert _is_persona_root_file(plb.Path(filename)) == expected


def test_source_file_properties(tmp_path: plb.Path) -> None:
    # Arrange
    content = b'test content'
    file_path = tmp_path / 'source' / 'subdir' / 'file.txt'
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(content)

    # Act
    sf = SourceFile(
        path=file_path,
        source_path_root=tmp_path / 'source',
        target_path_root='target/root',
    )

    # Assert
    assert sf.content == content
    # target_key should be target_path_root + relative path from source_path_root
    assert sf.target_key == 'target/root/subdir/file.txt'


def test_source_file_target_key_cleanup() -> None:
    # Arrange
    file_path = plb.Path('/a/b/.persona/c/file.txt')
    source_root = plb.Path('/a/b')

    # Act
    sf = SourceFile(
        path=file_path,
        source_path_root=source_root,
        target_path_root='roles/my-role',
    )

    # Assert
    # relpath is .persona/c/file.txt, .persona/ should be stripped
    assert sf.target_key == 'roles/my-role/c/file.txt'


def test_persona_root_source_file_metadata(tmp_path: plb.Path) -> None:
    # Arrange
    content = '---\nname: original\ndescription: old desc\n---\nbody'
    file_path = tmp_path / 'ROLE.md'
    file_path.write_text(content)

    sf = PersonaRootSourceFile(path=file_path)

    # Act
    updated_content = sf.update_metadata(name='new name', description='new desc')

    # Assert
    assert b'new name' in updated_content
    assert b'new desc' in updated_content
    assert b'body' in updated_content
    # sf.metadata is updated in-place because it's a reference to fm.metadata
    assert sf.metadata == {'name': 'new name', 'description': 'new desc'}


def test_template_invalid_path() -> None:
    with pytest.raises(ValidationError, match='Path does not exist'):
        Skill(path=plb.Path('non_existent_path'))


@pytest.mark.parametrize(
    ('cls', 'filename', 'valid'),
    [
        (Skill, 'SKILL.md', True),
        (Skill, 'ROLE.md', False),
        (Role, 'ROLE.md', True),
        (Role, 'SKILL.md', False),
    ],
)
def test_template_file_name_validation(
    tmp_path: plb.Path, cls: type, filename: str, valid: bool
) -> None:
    # Arrange
    path = tmp_path / filename
    path.touch()

    # Act & Assert
    if valid:
        obj = cls(path=path)
        assert obj.path == path
    else:
        with pytest.raises(ValidationError, match='is not a valid'):
            cls(path=path)


def test_template_directory_validation(tmp_path: plb.Path) -> None:
    # Arrange
    template_dir = tmp_path / 'my_skill'
    template_dir.mkdir()
    (template_dir / 'SKILL.md').touch()

    # Act
    skill = Skill(path=template_dir)

    # Assert
    assert skill.is_dir is True


def test_template_directory_validation_missing_file(tmp_path: plb.Path) -> None:
    # Arrange
    template_dir = tmp_path / 'empty_dir'
    template_dir.mkdir()

    # Act & Assert
    with pytest.raises(ValidationError, match='is not a valid SKILL.md template'):
        Skill(path=template_dir)


def test_template_metadata_extraction(tmp_path: plb.Path) -> None:
    # Arrange
    template_dir = tmp_path / 'my_role'
    template_dir.mkdir()
    (template_dir / 'ROLE.md').write_text('---\nname: role-name\n---')

    role = Role(path=template_dir)

    # Act
    metadata = role.metadata

    # Assert
    assert metadata == {'name': 'role-name'}


def test_process_template_full_cycle(tmp_path: plb.Path) -> None:
    # Arrange
    template_dir = tmp_path / 'my_skill'
    template_dir.mkdir()
    root_file = template_dir / 'SKILL.md'
    root_file.write_text('---\nname: skill-from-fm\ndescription: desc-from-fm\n---\ncontent')
    (template_dir / 'other.py').write_text('print("hello")')

    skill = Skill(path=template_dir)

    entry = IndexEntry()
    mock_file_store = MagicMock()
    mock_meta_engine = MagicMock()
    mock_embedder = MagicMock()
    mock_embedder.encode.return_value = np.zeros((1, 384))
    mock_tagger = MagicMock()
    mock_tagger.extract_tags.return_value = {'skill-from-fm': ['tag1']}

    # Act
    skill.process_template(
        entry=entry,
        target_file_store=mock_file_store,
        meta_store_engine=mock_meta_engine,
        embedder=mock_embedder,
        tagger=mock_tagger,
    )

    # Assert
    assert entry.name == 'skill-from-fm'
    assert entry.description == 'skill-from-fm - desc-from-fm'
    assert entry.type == 'skills'
    assert entry.tags == ['tag1']
    assert entry.embedding == [0.0] * 384
    assert len(entry.files) == 2
    assert any(f.endswith('SKILL.md') for f in entry.files)
    assert any(f.endswith('other.py') for f in entry.files)
    assert entry.etag is not None

    assert mock_file_store.save.call_count == 2
    mock_meta_engine.index.assert_called_once_with(entry)


def test_process_template_overrides(tmp_path: plb.Path) -> None:
    # Arrange
    root_file = tmp_path / 'SKILL.md'
    # Including tags in frontmatter prevents the tagger from being called
    root_file.write_text('---\nname: fm-name\ndescription: fm-desc\ntags: [fm-tag]\n---')
    skill = Skill(path=root_file)

    entry = IndexEntry(name='explicit-name', description='explicit-desc', tags=['manual'])
    mock_file_store = MagicMock()
    mock_meta_engine = MagicMock()
    mock_embedder = MagicMock()
    mock_embedder.encode.return_value = np.zeros((1, 384))
    mock_tagger = MagicMock()

    # Act
    skill.process_template(
        entry=entry,
        target_file_store=mock_file_store,
        meta_store_engine=mock_meta_engine,
        embedder=mock_embedder,
        tagger=mock_tagger,
    )

    # Assert
    assert entry.name == 'explicit-name'
    assert entry.description == 'explicit-name - explicit-desc'
    assert entry.tags == ['manual']
    mock_tagger.extract_tags.assert_not_called()


def test_process_template_missing_metadata_error(tmp_path: plb.Path) -> None:
    # Arrange
    root_file = tmp_path / 'SKILL.md'
    root_file.write_text('---\n---')  # No name/description
    skill = Skill(path=root_file)

    entry = IndexEntry()
    mock_file_store = MagicMock()
    mock_meta_engine = MagicMock()
    mock_embedder = MagicMock()
    mock_tagger = MagicMock()

    # Act & Assert
    with pytest.raises(ValueError, match='Template must have a name and description'):
        skill.process_template(
            entry=entry,
            target_file_store=mock_file_store,
            meta_store_engine=mock_meta_engine,
            embedder=mock_embedder,
            tagger=mock_tagger,
        )


def test_template_file_adapter_discriminator(tmp_path: plb.Path) -> None:
    # Arrange
    skill_file = tmp_path / 'SKILL.md'
    skill_file.touch()
    role_file = tmp_path / 'ROLE.md'
    role_file.touch()

    # Act
    skill_obj = TemplateFile.validate_python({'type': 'skills', 'path': str(skill_file)})
    role_obj = TemplateFile.validate_python({'type': 'roles', 'path': str(role_file)})

    # Assert
    assert isinstance(skill_obj, Skill)
    assert isinstance(role_obj, Role)
