import os
import pathlib as plb
import logging
from typing import cast

import frontmatter
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File

from persona.storage import (
    BaseMetaStoreSession,
    BaseFileStore,
)
from persona.embedder import FastEmbedder
from persona.types import personaTypes
from persona.mcp.models import TemplateDetails, SkillFile, TemplateMatch
from persona.mcp.utils.const import EXT_WHITELIST
from persona.mcp.utils.lib import library_skills

logger = logging.getLogger('persona.mcp.utils.retrieval')


def _list(type: personaTypes, session: BaseMetaStoreSession) -> list[dict]:
    """List all personas (logic)."""
    return session.get_many(
        table_name=type,
        column_filter=['name', 'description', 'uuid'],
    ).to_pylist()


def _write_skill_files(
    local_skill_dir: str,
    name: str,
    meta_store: BaseMetaStoreSession,
    file_store: BaseFileStore,
):
    """Write skill files to a local directory where the LLM can access them."""
    dir_ = plb.Path(local_skill_dir)
    skill_file: str | None = None
    if not dir_.is_absolute():
        raise ToolError(
            f'Target skill directory "{local_skill_dir}" is not an absolute path. Please provide an absolute path.'
        )
    elif not dir_.exists():
        raise ToolError(
            f'Target skill directory "{local_skill_dir}" does not exist. Please create it before installing the skill.'
        )

    skill_files = library_skills.get(name, None) or _skill_files(file_store, meta_store, name)

    for name, file in skill_files.items():
        dest = dir_ / file.storage_file_path.replace('skills/', '')
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
        with plb.Path(dest).open('wb') as f:
            f.write(file.content)
        if file.name == 'SKILL.md':
            skill_file = str(dest)
    if skill_file is None:
        raise ToolError(
            f'SKILL.md file not found for skill "{name}". Installation may have failed.'
        )
    return skill_file


def _get_skill_version(name: str, meta_store: BaseMetaStoreSession) -> str:
    """Get a skill version by name (logic)."""
    if meta_store.exists('skills', name):
        skill_files = cast(
            dict[str, str],
            meta_store.get_one('skills', name, ['name', 'files', 'uuid']).to_pylist()[0],
        )
        return skill_files['uuid']
    else:
        raise ToolError(f'Skill "{name}" not found')


def _skill_files(
    file_store: BaseFileStore, meta_store: BaseMetaStoreSession, name: str
) -> dict[str, SkillFile]:
    """Get a skill by name (logic)."""
    if meta_store.exists('skills', name):
        skill_files = cast(
            dict[str, str],
            meta_store.get_one('skills', name, ['name', 'files', 'uuid']).to_pylist()[0],
        )
        content = frontmatter.loads(file_store.load(f'skills/{name}/SKILL.md').decode('utf-8'))
        content.metadata['metadata'] = {'version': skill_files['uuid']}
        results = {
            'SKILL.md': SkillFile(
                content=frontmatter.dumps(content).encode('utf-8'),
                name='SKILL.md',
                storage_file_path=f'skills/{name}/SKILL.md',
                extension='.md',
            )
        }
        for target_store_file in skill_files['files']:
            file = target_store_file.rsplit('/', 1)[-1]
            ext = os.path.splitext(file)[-1]
            if ext not in EXT_WHITELIST:
                continue
            elif file.endswith('SKILL.md'):
                continue
            else:
                _file_content = file_store.load(target_store_file)
                results[file] = SkillFile(
                    content=_file_content,
                    name=file,
                    storage_file_path=target_store_file,
                    extension=ext,
                )
        return results
    else:
        raise ToolError(f'Skill "{name}" not found')


def _get_skill(
    name: str,
    meta_store: BaseMetaStoreSession,
    file_store: BaseFileStore,
) -> list[File]:
    """Get a skill by name (logic)."""
    results = []
    for name, skill in (_skill_files(file_store, meta_store, name)).items():
        results.append(
            File(
                data=skill.content,
                name=skill.name,
                format='text',
            )
        )
    return results


def _get_persona(
    name: str,
    meta_store: BaseMetaStoreSession,
    file_store: BaseFileStore,
) -> TemplateDetails:
    """Get a persona by name (logic)."""
    if meta_store.exists('roles', name):
        content = frontmatter.loads(file_store.load(f'roles/{name}/ROLE.md').decode('utf-8'))
        return TemplateDetails(
            name=name,
            description=cast(str, content.metadata.get('description', '')),
            prompt=content.content.strip(),
        )
    else:
        raise ToolError(f'Role "{name}" not found')


def _match(
    type: personaTypes,
    query_string: str,
    embedding_model: FastEmbedder,
    meta_store: BaseMetaStoreSession,
    limit: int | None = None,
    max_cosine_distance: float | None = None,
) -> list[TemplateMatch]:
    """Match a persona to the provided description (logic)."""
    query = embedding_model.encode([query_string]).squeeze().tolist()
    return [
        TemplateMatch(**item)
        for item in meta_store.search(
            query=query,
            table_name=type,
            limit=cast(int, limit),
            column_filter=['uuid', 'name', 'description'],
            max_cosine_distance=cast(float, max_cosine_distance),
        ).to_pylist()
    ]
