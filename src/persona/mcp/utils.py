import os
import pathlib as plb
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast, Literal

import yaml
import frontmatter
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from persona.config import StorageConfig, parse_storage_config
from persona.storage import get_storage_backend, VectorDatabase

from .models import AppContext, TemplateDetails


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


async def _get(type: Literal['personas', 'skills'], ctx: AppContext, name: str) -> TemplateDetails:
    """Get a skill by name (logic)."""
    root_name = 'SKILL.md' if type == 'skills' else 'PERSONA.md'
    if ctx._vector_db.exists(type, name):
        content = frontmatter.loads(
            ctx._target_storage.load(f'{type}/{name}/{root_name}').decode('utf-8')
        )
        return TemplateDetails(
            name=name,
            description=cast(str, content.metadata.get('description', '')),
            prompt=content.content.strip(),
        )
    else:
        raise ToolError(f'{type} "{name}" not found')


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
