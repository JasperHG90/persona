import asyncio
from typing import cast
import pathlib as plb

import aiofiles
from fastmcp import FastMCP, Context
from mcp.shared.context import RequestContext

from .models import AppContext, TemplateDetails
from .utils import (
    _list,
    _get,
    _match,
    lifespan,
)

prompts_dir = plb.Path(__file__).parent / 'prompts'

mcp = FastMCP('persona_mcp', version='0.1.0', lifespan=lifespan)


@mcp.tool(description='List all available personas.')
async def list_personas(ctx: Context) -> list[dict]:
    """List all personas."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _list('personas', app_context)


@mcp.tool(description='List all available skills.')
async def list_skills(ctx: Context) -> list[dict]:
    """List all skills."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _list('skills', app_context)


@mcp.tool(
    '/skills/{name}',
    description='Get a skill by name.',
)
async def get_skill(ctx: Context, name: str) -> TemplateDetails:
    """Get a skill by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _get('skills', app_context, name)


@mcp.tool(
    '/personas/{name}',
    description='Get a persona by name.',
)
async def get_persona(ctx: Context, name: str) -> TemplateDetails:
    """Get a persona by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _get('personas', app_context, name)


@mcp.tool('/personas/match', description='Match a persona to the provided description.')
async def match_persona(
    ctx: Context,
    description: str,
    limit: int = 5,
    max_cosine_distance: float = 0.7,
) -> list[dict]:
    """Match a persona to the provided description."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _match('personas', description, app_context, limit, max_cosine_distance)


@mcp.tool('/skills/match', description='Match a skill to the provided description.')
async def match_skill(
    ctx: Context,
    description: str,
    limit: int = 5,
    max_cosine_distance: float = 0.7,
) -> list[dict]:
    """Match a skill to the provided description."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _match('skills', description, app_context, limit, max_cosine_distance)


@mcp.prompt(
    name='persona:roleplay', description='Assume a persona based on the provided description.'
)
async def persona_roleplay(description: str) -> str:
    async with aiofiles.open(prompts_dir / 'roleplay.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Description: {description}
    """
    return template + '\n' + user_instructions.strip()


@mcp.prompt(
    name='persona:template', description='Prompt engineering template for creating a new persona.'
)
async def persona_template(description: str) -> str:
    async with aiofiles.open(prompts_dir / 'template.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Description: {description}
    """
    return template + '\n' + user_instructions.strip()


@mcp.prompt(
    name='persona:review', description='Review a persona definition for quality and completeness.'
)
async def persona_review(persona: str, chat_history: str | None = None) -> str:
    async with aiofiles.open(prompts_dir / 'review.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Persona Definition:
    {persona}

    Chat History (optional):
    {chat_history or 'N/A'}
    """
    return template + '\n' + user_instructions.strip()


@mcp.prompt(name='persona:edit', description='Edit a persona definition based on feedback.')
async def persona_edit(persona: str, feedback: str) -> str:
    async with aiofiles.open(prompts_dir / 'edit.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Persona Definition:
    {persona}

    Feedback:
    {feedback}
    """
    return template + '\n' + user_instructions.strip()


def entrypoint():
    """
    Entrypoint for the MCP server.
    """
    asyncio.run(mcp.run_async(transport='stdio'))


if __name__ == '__main__':
    entrypoint()
