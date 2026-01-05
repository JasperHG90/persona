from unittest.mock import MagicMock, patch
import pathlib as plb
from persona.mcp.utils.lib import _get_builtin_skills


def test_get_builtin_skills() -> None:
    # Arrange
    mock_path = MagicMock(spec=plb.Path)

    # Structure:
    # library/assets/skills/
    #   skill1/
    #     SKILL.md
    #     script.py
    #   skill2/
    #     SKILL.md

    mock_skill1_md = MagicMock(spec=plb.Path)
    mock_skill1_md.name = 'SKILL.md'
    mock_skill1_md.parent.name = 'skill1'
    mock_skill1_md.read_bytes.return_value = b'skill1 content'
    mock_skill1_md.suffix = '.md'
    mock_skill1_md.relative_to.return_value = plb.Path('skill1/SKILL.md')
    mock_skill1_md.is_dir.return_value = False

    mock_skill1_script = MagicMock(spec=plb.Path)
    mock_skill1_script.name = 'script.py'
    mock_skill1_script.parent.name = 'skill1'  # parent name is consistent
    mock_skill1_script.read_bytes.return_value = b"print('hello')"
    mock_skill1_script.suffix = '.py'
    mock_skill1_script.relative_to.return_value = plb.Path('skill1/script.py')
    mock_skill1_script.is_dir.return_value = False

    mock_skill2_md = MagicMock(spec=plb.Path)
    mock_skill2_md.name = 'SKILL.md'
    mock_skill2_md.parent.name = 'skill2'
    mock_skill2_md.read_bytes.return_value = b'skill2 content'
    mock_skill2_md.suffix = '.md'
    mock_skill2_md.relative_to.return_value = plb.Path('skill2/SKILL.md')
    mock_skill2_md.is_dir.return_value = False

    # The glob for SKILL.md
    mock_path.glob.side_effect = lambda pattern: {
        '*/SKILL.md': [mock_skill1_md, mock_skill2_md],
    }.get(pattern, [])

    # The recursive glob for files in skill dir
    # We need to make sure mock_skill1_md.parent returns the mock that we set glob on.
    # MagicMock creates a new mock on access if not set.

    mock_skill1_dir = MagicMock()
    mock_skill1_dir.name = 'skill1'
    mock_skill1_dir.glob.return_value = [mock_skill1_md, mock_skill1_script]
    mock_skill1_md.parent = mock_skill1_dir
    mock_skill1_script.parent = mock_skill1_dir

    mock_skill2_dir = MagicMock()
    mock_skill2_dir.name = 'skill2'
    mock_skill2_dir.glob.return_value = [mock_skill2_md]
    mock_skill2_md.parent = mock_skill2_dir

    # Important: The code iterates `library_skills_path.glob(...)`.
    # It gets `skill_path` (e.g. mock_skill1_md).
    # Then access `skill_path.parent`.
    # So `mock_skill1_md.parent` must be `mock_skill1_dir`.

    with patch('persona.mcp.utils.lib.library_skills_path', mock_path):
        # Act
        skills = _get_builtin_skills()

        # Assert
        assert 'skill1' in skills
        assert 'skill2' in skills

        assert 'SKILL.md' in skills['skill1']
        assert 'script.py' in skills['skill1']
        assert skills['skill1']['SKILL.md'].content == b'skill1 content'
        assert skills['skill1']['script.py'].content == b"print('hello')"

        assert 'SKILL.md' in skills['skill2']
        assert 'script.py' not in skills['skill2']
