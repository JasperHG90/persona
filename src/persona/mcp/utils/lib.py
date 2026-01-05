import pathlib as plb
import logging
from collections import defaultdict

from persona.models import SkillFile

logger = logging.getLogger('persona.mcp.utils.lib')

library_skills_path = plb.Path(__file__).parent.parent / 'assets' / 'skills'


def _get_builtin_skills() -> dict[str, dict[str, SkillFile]]:
    """Get all skills that are part of this MCP library."""
    skills: dict[str, dict[str, SkillFile]] = defaultdict(dict)
    for skill_path in library_skills_path.glob('*/SKILL.md'):
        skill_name = skill_path.parent.name
        for fn in skill_path.parent.glob('**/*'):
            if fn.is_dir():
                continue
            ext = fn.suffix
            name = fn.name
            skills[skill_name][name] = SkillFile(
                content=fn.read_bytes(),
                name=name,
                storage_file_path=str(fn.relative_to(library_skills_path)),
                extension=ext,
            )
    return skills


library_skills = _get_builtin_skills()
