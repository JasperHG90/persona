import os
import pathlib as plb
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast

import yaml
import frontmatter
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from persona.config import StorageConfig, parse_storage_config
from persona.storage import Index, IndexEntry, get_storage_backend

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
    index = Index.model_validate_json(storage_backend.load(config.root.index))
    app_context = AppContext(config=config, index=index)
    app_context._target_storage = storage_backend
    yield app_context


async def _list_personas_logic(ctx: AppContext) -> list[IndexEntry]:
    """List all personas (logic)."""
    return [
        IndexEntry(
            name=persona.name,
            description=persona.description,
            uuid=persona.uuid,
        )
        for persona in ctx.index.personas.root.values()
    ]


async def _list_skills_logic(ctx: AppContext) -> list[IndexEntry]:
    """List all skills (logic)."""
    return [
        IndexEntry(
            name=skill.name,
            description=skill.description,
            uuid=skill.uuid,
        )
        for skill in ctx.index.skills.root.values()
    ]


async def _get_skill_logic(ctx: AppContext, name: str) -> TemplateDetails:
    """Get a skill by name (logic)."""
    skill: IndexEntry | None = ctx.index.skills.root.get(name)
    if skill:
        content = frontmatter.loads(
            ctx._target_storage.load('skills/%s/%s' % (skill.name, 'SKILL.md'))
        )
        return TemplateDetails(
            name=cast(str, skill.name),
            description=cast(str, skill.description),
            prompt=content.content.strip(),
        )
    raise ToolError('Skill not found')


async def _get_persona_logic(ctx: AppContext, name: str) -> TemplateDetails:
    """Get a persona by name (logic)."""
    persona: IndexEntry | None = ctx.index.personas.root.get(name)
    if persona:
        content = frontmatter.loads(
            ctx._target_storage.load('personas/%s/%s' % (persona.name, 'PERSONA.md'))
        )
        return TemplateDetails(
            name=cast(str, persona.name),
            description=cast(str, persona.description),
            prompt=content.content.strip(),
        )
    raise ToolError('Persona not found')


async def _add_persona_logic(ctx: AppContext, name: str, description: str):
    """Add a new persona (logic)."""
    return f"persona personas register <PATH> --name {name} --description '{description}'"


async def _add_skill_logic(ctx: AppContext, name: str, description: str):
    """Add a new skill (logic)."""
    return f"persona skills register <PATH> --name {name} --description '{description}'"
