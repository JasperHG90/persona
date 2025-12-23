import asyncio
from typing import cast, Annotated
import pathlib as plb

import aiofiles
from fastmcp import FastMCP, Context
from fastmcp.utilities.types import File
from mcp.shared.context import RequestContext
from pydantic import Field

from .models import AppContext, TemplateDetails
from .utils import (
    _list,
    _match,
    _get_persona,
    _get_skill,
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
    name="get_skill",
    description="""
    RETRIEVAL PROTOCOL:
    1. This tool returns a list of File objects representing a Skill Package.
    2. Each File object has a 'name' field which is the REQUIRED relative path.
    3. You must use an appropriate tool to save each file to the path specified
    in its 'name' field.
    4. CRITICAL: You must perform a 1:1 raw copy. Do NOT remove metadata blocks 
       like '# /// script'. Do NOT summarize or 'clean' the code.
    5. **DO NOT** create any extra files beyond what is provided with the exception of required subdirectories.
    6. You **MUST** follow the execution logic in SKILL.md after writing all files. Do **NOT** attempt to execute
    any code, install any dependencies etc. without following the explicit instructions in the SKILL.md file.
    """
)
async def get_skill(ctx: Context, name: Annotated[str, Field(description="Name of the skill to retrieve.")]) -> list[File]:
    """Get a skill by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _get_skill(app_context, name)


@mcp.tool(
    name="get_persona",
    description='Get a persona by name.',
)
async def get_persona(ctx: Context, name: Annotated[str, Field(description="Name of the persona to retrieve.")]) -> TemplateDetails:
    """Get a persona by name."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _get_persona(app_context, name)


@mcp.tool(
    name="match_persona",
    description="""Searches the Persona registry for relevant roles or prompts based
    on a natural language description. Use this tool when users ask for a specific role
    or some natural language description of a prompt.
    
    EXAMPLES:
    - "You are an expert JavaScript developer who writes clean and efficient code."
    - "Go expert data scientist skilled in Python and machine learning."
         
    OUTPUT: Returns a list of matching prompt names and their descriptions from the registry
    for matches within the specified cosine distance threshold and a maximum number of results."""
)
async def match_persona(
    ctx: Context,
    query: Annotated[str, Field(description="Natural language description of the prompt or role needed.")],
    limit: Annotated[int, Field(description="Maximum number of results to return.")] = 5,
    max_cosine_distance: Annotated[float, Field(description="Maximum cosine distance threshold for matches.")] = 0.7,
) -> list[dict]:
    """Match a persona to the provided description."""
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return await _match('personas', query, app_context, limit, max_cosine_distance)


@mcp.tool( 
    name="match_skill",
    description="""Searches the Persona registry for relevant skills or capabilities. 
    Use this tool whenever the user asks for a task that you don't have a 
    built-in tool for (e.g., 'scrape web', 'optimize code').
    
    OUTPUT: Returns a list of matching skill names and their descriptions from the registry
    for matches within the specified cosine distance threshold and a maximum number of results."""
)
async def match_skill(
    ctx: Context,
    query: Annotated[str, Field(description="Natural language description of the task or capability needed.")],
    limit: Annotated[int, Field(description="Maximum number of results to return.")] = 5,
    max_cosine_distance: Annotated[float, Field(description="Maximum cosine distance threshold for matches.")] = 0.7,
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


def entrypoint():
    """
    Entrypoint for the MCP server.
    """
    asyncio.run(mcp.run_async(transport='stdio'))


if __name__ == '__main__':
    entrypoint()
