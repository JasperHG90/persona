import os
import pathlib as plb
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast, Generator, Annotated
from collections import defaultdict

import yaml
import frontmatter
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File
from fastmcp.dependencies import Depends
from mcp.shared.context import RequestContext

from persona.config import parse_persona_config, PersonaConfig
from persona.storage import (
    get_file_store_backend,
    get_meta_store_backend,
    BaseMetaStore,
    BaseFileStore,
)
from persona.embedder import get_embedding_model, FastEmbedder
from persona.types import personaTypes

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
        config_validated = PersonaConfig.model_validate(config_raw).model_dump()
        config = parse_persona_config(config_validated)
    else:
        config = parse_persona_config({})  # Will be read from env vars
    file_store = get_file_store_backend(config.file_store)
    # NB: read_only prevents changes from being persisted
    meta_store_engine = get_meta_store_backend(config.meta_store, read_only=True)
    meta_store_engine.connect()
    meta_store_engine.bootstrap()
    app_context = AppContext(config=config)
    app_context._file_store = file_store
    app_context._meta_store_engine = meta_store_engine
    app_context._embedding_model = get_embedding_model()
    yield app_context
    meta_store_engine.close()


def get_meta_store_session(ctx: Context) -> Generator[BaseMetaStore, None, None]:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    meta_store = app_context._meta_store_engine
    with meta_store.session() as session:
        yield session


def get_file_store(ctx: Context) -> BaseFileStore:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context._file_store


def get_embedder(ctx: Context) -> FastEmbedder:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context._embedding_model


def get_config(ctx: Context) -> PersonaConfig:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context.config


def _list(type: personaTypes, session: BaseMetaStore) -> list[dict]:
    """List all personas (logic)."""
    return session.get_many(
        table_name=type,
        column_filter=['name', 'description', 'uuid'],
    )


def _write_skill_files(
    local_skill_dir: str,
    name: str,
    meta_store: BaseMetaStore,
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


def _get_skill_version(name: str, meta_store: BaseMetaStore) -> str:
    """Get a skill version by name (logic)."""
    if meta_store.exists('skills', name):
        skill_files = cast(
            dict[str, str], meta_store.get_one('skills', name, ['name', 'files', 'uuid'])
        )
        return skill_files['uuid']
    else:
        raise ToolError(f'Skill "{name}" not found')


def _skill_files(
    file_store: BaseFileStore, meta_store: BaseMetaStore, name: str
) -> dict[str, SkillFile]:
    """Get a skill by name (logic)."""
    if meta_store.exists('skills', name):
        skill_files = cast(
            dict[str, str], meta_store.get_one('skills', name, ['name', 'files', 'uuid'])
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
            ext = plb.Path(file).suffix
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
    meta_store: Annotated[BaseMetaStore, Depends(get_meta_store_session)],
    file_store: BaseFileStore = Depends(get_file_store),
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
    meta_store: BaseMetaStore,
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
    config: PersonaConfig,
    meta_store: BaseMetaStore,
    limit: int | None = None,
    max_cosine_distance: float | None = None,
) -> list[dict[str, str]]:
    """Match a persona to the provided description (logic)."""
    query = embedding_model.encode(query_string).tolist()
    if limit is None:
        limit = config.meta_store.similarity_search.max_results
    if max_cosine_distance is None:
        max_cosine_distance = config.meta_store.similarity_search.max_cosine_distance
    return meta_store.search(
        query=query,
        table_name=type,
        limit=cast(int, limit),
        column_filter=['uuid', 'name', 'description'],
        max_cosine_distance=cast(float, max_cosine_distance),
    ).to_pylist()
