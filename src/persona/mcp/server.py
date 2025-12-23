import asyncio
from typing import cast, Annotated
import pathlib as plb

import aiofiles
from fastmcp import FastMCP, Context
from mcp.shared.context import RequestContext
from pydantic import Field

from .models import AppContext, TemplateDetails
from .utils import (
    _list,
    _match,
    _get_persona,
    _write_skill_files,
    _get_skill_version,
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


# NB: this only works if the MCP is running locally so it can write files to disk
@mcp.tool(
    name='install_skill',
    description="""
    RETRIEVAL PROTOCOL:
    1. This tool installs a Skill by installing it to the specified **absolute** target root directory.
    2. The **absolute** target root directory must exist prior to calling this tool.
    3. After installation, the SKILL.md file will be available in <target_skill_dir>/<skill_name>/SKILL.md.
    4. You **MUST** read the SKILL.md file and follow the execution instructions specified there.
    """,
)
async def install_skill(
    ctx: Context,
    name: Annotated[str, Field(description='Name of the skill to retrieve.')],
    target_skill_dir: Annotated[
        str,
        Field(
            description="""
        The **absolute** path to the root directory where the skill will be stored in the current project.
        This directory **must** exist prior to calling this tool. This tool will create all necessary
        subdirectories under this root directory to store the skill files.
        """,
            examples=[
                '/home/vscode/project/.skills',
                '/Users/johndoe/projects/.persona/skills',
                '/mnt/data/.persona/skills',
            ],
        ),
    ],
) -> str:
    """Get a skill by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _write_skill_files(app_context, target_skill_dir, name)


@mcp.tool(
    name='get_skill_version',
    description='Get a skill version by name.',
)
async def get_skill_version(
    ctx: Context,
    name: Annotated[str, Field(description='Name of the skill to retrieve the version for.')],
) -> str:
    """Get a skill version by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _get_skill_version(app_context, name)


@mcp.tool(
    name='get_persona',
    description='Get a persona by name.',
)
async def get_persona(
    ctx: Context, name: Annotated[str, Field(description='Name of the persona to retrieve.')]
) -> TemplateDetails:
    """Get a persona by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _get_persona(app_context, name)


@mcp.tool(
    name='match_persona',
    description="""Searches the Persona registry for relevant roles or prompts based
    on a natural language description. Use this tool when users ask for a specific role
    or some natural language description of a prompt.

    EXAMPLES:
    - "You are an expert JavaScript developer who writes clean and efficient code."
    - "Go expert data scientist skilled in Python and machine learning."

    OUTPUT: Returns a list of matching prompt names and their descriptions from the registry
    for matches within the specified cosine distance threshold and a maximum number of results.""",
)
async def match_persona(
    ctx: Context,
    query: Annotated[
        str, Field(description='Natural language description of the prompt or role needed.')
    ],
    limit: Annotated[int, Field(description='Maximum number of results to return.')] = 5,
    max_cosine_distance: Annotated[
        float, Field(description='Maximum cosine distance threshold for matches.')
    ] = 0.7,
) -> list[dict]:
    """Match a persona to the provided description."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _match('personas', query, app_context, limit, max_cosine_distance)


@mcp.tool(
    name='match_skill',
    description="""Searches the Persona registry for relevant skills or capabilities.
    Use this tool whenever the user asks for a task that you don't have a
    built-in tool for (e.g., 'scrape web', 'optimize code').

    OUTPUT: Returns a list of matching skill names and their descriptions from the registry
    for matches within the specified cosine distance threshold and a maximum number of results.""",
)
async def match_skill(
    ctx: Context,
    query: Annotated[
        str, Field(description='Natural language description of the task or capability needed.')
    ],
    limit: Annotated[int, Field(description='Maximum number of results to return.')] = 5,
    max_cosine_distance: Annotated[
        float, Field(description='Maximum cosine distance threshold for matches.')
    ] = 0.7,
) -> list[dict]:
    """Match a skill to the provided description."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _match('skills', query, app_context, limit, max_cosine_distance)


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


@mcp.prompt(
    name='skill:deploy', description='Execute a prompt with explicit skill deployment instructions.'
)
async def skill_deploy(task: str) -> str:
    async with aiofiles.open(prompts_dir / 'skill_deploy.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Task description: {task}
    """
    return template + '\n' + user_instructions.strip()


@mcp.prompt(
    name='skill:update', description='Update a specific skill if a new version is available.'
)
async def skill_update(
    name: Annotated[str, Field(description='Name of the skill to update.')],
) -> str:
    async with aiofiles.open(prompts_dir / 'skill_update.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Skill name: {name}
    """
    return template + '\n' + user_instructions.strip()


def entrypoint():
    """
    Entrypoint for the MCP server.
    """
    asyncio.run(mcp.run_async(transport='stdio'))


if __name__ == '__main__':
    entrypoint()
