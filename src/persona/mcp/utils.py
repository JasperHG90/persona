import os
import pathlib as plb
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast, Literal
from collections import defaultdict

import yaml
import frontmatter
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File

from persona.config import StorageConfig, parse_storage_config
from persona.storage import get_storage_backend, VectorDatabase

from .models import AppContext, TemplateDetails, SkillFile

EXT_WHITELIST = [
    '.md',
    '.txt',
    '.json',
    '.yaml',
    '.yml',
    '.cfg',
    '.ini',
    '.py',
    '.js',
    '.ts',
    '.html',
    '.css',
]

library_skills_path = plb.Path(__file__).parent / 'assets' / 'skills'


def _get_builtin_skills() -> dict[str, dict[str, SkillFile]]:
    """Get all skills that are part of this MCP library."""
    skills = defaultdict(dict)
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


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Lifespan context manager for the the persona MCP server. Loads storage backend, configuration
    and index.
    """
    persona_config_path = (
        plb.Path.home() / '.persona.config.yaml'
        if not os.environ.get('PERSONA_CONFIG_PATH', None)
        else plb.Path(os.environ['PERSONA_CONFIG_PATH'])
    )
    if persona_config_path.exists():
        with persona_config_path.open('r') as f:
            config_raw = yaml.safe_load(f) or {}
        config = StorageConfig.model_validate(config_raw)
    else:
        config = parse_storage_config({})  # Will be read from env vars
    storage_backend = get_storage_backend(config.root)
    vector_db = VectorDatabase(uri=config.root.index_path, optimize=False)
    app_context = AppContext(config=config)
    app_context._target_storage = storage_backend
    app_context._vector_db = vector_db
    yield app_context


async def _list(type: Literal['personas', 'skills'], ctx: AppContext) -> list[dict]:
    """List all personas (logic)."""
    return (
        ctx._vector_db.get_or_create_table(type)
        .to_arrow()
        .select(['name', 'description', 'uuid'])
        .to_pylist()
    )


async def _write_skill_files(
    ctx: AppContext,
    target_skill_dir: str,
    name: str,
):
    """Write skill files to a local directory where the LLM can access them."""
    dir_ = plb.Path(target_skill_dir)
    skill_file: str | None = None
    if not dir_.is_absolute():
        raise ToolError(
            f'Target skill directory "{target_skill_dir}" is not an absolute path. Please provide an absolute path.'
        )
    elif not dir_.exists():
        raise ToolError(
            f'Target skill directory "{target_skill_dir}" does not exist. Please create it before installing the skill.'
        )

    skill_files = library_skills.get(name, None) or await _skill_files(ctx, name)

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


async def _get_skill_version(ctx: AppContext, name: str) -> str:
    """Get a skill version by name (logic)."""
    if ctx._vector_db.exists('skills', name):
        skill_files = cast(
            dict[str, str], ctx._vector_db.get_record('skills', name, ['name', 'files', 'uuid'])
        )
        return skill_files['uuid']
    else:
        raise ToolError(f'Skill "{name}" not found')


async def _skill_files(ctx: AppContext, name: str) -> dict[str, SkillFile]:
    """Get a skill by name (logic)."""
    if ctx._vector_db.exists('skills', name):
        skill_files = cast(
            dict[str, str], ctx._vector_db.get_record('skills', name, ['name', 'files', 'uuid'])
        )
        content = frontmatter.loads(
            ctx._target_storage.load(f'skills/{name}/SKILL.md').decode('utf-8')
        )
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
            ext = plb.Path(file).suffix
            if ext not in EXT_WHITELIST:
                continue
            elif file.endswith('SKILL.md'):
                continue
            else:
                _file_content = ctx._target_storage.load(target_store_file)
                results[file] = SkillFile(
                    content=_file_content,
                    name=file,
                    storage_file_path=target_store_file,
                    extension=ext,
                )
        return results
    else:
        raise ToolError(f'Skill "{name}" not found')


async def _get_skill(ctx: AppContext, name: str) -> list[File]:
    """Get a skill by name (logic)."""
    results = []
    for name, skill in (await _skill_files(ctx, name)).items():
        results.append(
            File(
                data=skill.content,
                name=skill.name,
                format='text',
            )
        )
    return results


async def _get_persona(ctx: AppContext, name: str) -> TemplateDetails:
    """Get a persona by name (logic)."""
    if ctx._vector_db.exists('personas', name):
        content = frontmatter.loads(
            ctx._target_storage.load(f'personas/{name}/PERSONA.md').decode('utf-8')
        )
        return TemplateDetails(
            name=name,
            description=cast(str, content.metadata.get('description', '')),
            prompt=content.content.strip(),
        )
    else:
        raise ToolError(f'Persona "{name}" not found')


async def _match(
    type: Literal['personas', 'skills'],
    description: str,
    ctx: AppContext,
    limit: int = 5,
    max_cosine_distance: float = 0.7,
) -> list[dict]:
    """Match a persona to the provided description (logic)."""
    return (
        ctx._vector_db.search(
            query=description, table_name=type, limit=limit, max_cosine_distance=max_cosine_distance
        )
        .to_arrow()
        .select(['uuid', 'name', 'description', '_distance'])
        .to_pylist()
    )
