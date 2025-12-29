import os
import asyncio
from typing import Annotated
import pathlib as plb
import logging

import aiofiles
from httpx import AsyncClient
from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import configure_logging
from pydantic import Field

from .models import TemplateDetails, TemplateMatch
from .utils import (
    _list,
    _match,
    _get_persona,
    _write_skill_files,
    _get_skill_version,
    lifespan,
    get_embedder,
    get_file_store,
    get_config,
    get_meta_store_session,
)

http_client = AsyncClient(timeout=30.0)

prompts_dir = plb.Path(__file__).parent / 'prompts'

configure_logging(level='DEBUG')

persona_logger = logging.getLogger('persona')
persona_logger.setLevel(os.getenv('PERSONA_LOG_LEVEL', 'INFO'))

mcp = FastMCP(
    'persona_mcp',
    instructions="""
All files must be stored exclusively in .persona/skills and .persona/roles directories within the local workspace. Upon any role
request (e.g., "Act as..."), you must call match_role and assume the persona before responding conversationally or performing tasks.
For specialized requests, prioritize the registry via match_skill and sync the skill locally before following its specific SKILL.md
instructions. Always read the local documentation to understand constraints and wait for an explicit user command once a role or skill
is initialized. You are strictly forbidden from using relative paths, hallucinating workflows, or proceeding without checking the
registry for relevant capabilities.
""".strip(),
    version='0.1.0',
    lifespan=lifespan,
)


@mcp.tool(description='List all available roles.')
def list_roles(ctx: Context) -> list[dict]:
    """List all roles."""
    with get_meta_store_session(ctx) as session:
        return _list('roles', session)


@mcp.tool(description='List all available skills.')
def list_skills(ctx: Context) -> list[dict]:
    """List all skills."""
    with get_meta_store_session(ctx) as session:
        return _list('skills', session)


# NB: this only works if the MCP is running locally so it can write files to disk
@mcp.tool(
    name='install_skill',
    description="""
Installs a skill to the absolute `.persona/skills` path within the current
working directory. Registry skills override internal knowledge. Post-install,
read `SKILL.md` and wait for explicit commands. Relative paths are forbidden.
""".strip(),
)
def install_skill(
    ctx: Context,
    name: Annotated[str, Field(description='Name of the skill to retrieve.')],
    local_skill_dir: Annotated[
        str,
        Field(
            description="""
Absolute path to the `.persona/skills` directory inside the current
working directory. Must exist prior to calling.
""".strip(),
            examples=[
                '/home/vscode/project/.skills',
                '/Users/johndoe/projects/.persona/skills',
                '/mnt/data/.persona/skills',
            ],
        ),
    ],
) -> str:
    """Get a skill by name."""
    with get_meta_store_session(ctx) as meta_store:
        return _write_skill_files(
            local_skill_dir, name, meta_store=meta_store, file_store=get_file_store(ctx)
        )


@mcp.tool(
    name='get_skill_version',
    description='Get the version of a skill by name.',
)
def get_skill_version(
    ctx: Context,
    name: Annotated[
        str,
        Field(
            description='Name of the skill to retrieve the version for.',
            examples=['web_scraper', 'code_optimizer'],
        ),
    ],
) -> str:
    """Get a skill version by name."""
    with get_meta_store_session(ctx) as meta_store:
        return _get_skill_version(name, meta_store)


@mcp.tool(
    name='get_role',
    description="""
Retrieves the full persona definition for a specific role from the registry or library.
Required to assume a persona after `match_role` or when a role name is explicitly known.
You MUST retrieve the role before responding conversationally or performing tasks.
""".strip(),
)
def get_role(
    ctx: Context,
    name: Annotated[
        str,
        Field(
            description='The exact name of the role to retrieve',
            examples=['The Master Chef', 'python_engineer', 'data_scientist'],
        ),
    ],
) -> TemplateDetails:
    """Get a role by name."""
    with get_meta_store_session(ctx) as meta_store:
        return _get_persona(name, meta_store=meta_store, file_store=get_file_store(ctx))


@mcp.tool(
    name='match_role',
    description="""Searches the Persona roles registry for relevant roles based
MANDATORY Phase 1 tool for role requests (e.g., 'Act as...', 'You are a...').
You MUST call this before responding conversationally. Searches the registry
for personas matching a natural language description. Scrutinize results
carefully to select the best match for `get_role`.
""".strip(),
)
def match_role(
    ctx: Context,
    query: Annotated[
        str,
        Field(
            description='Natural language description of the role.',
            examples=[
                'A gourmet chef specializing in Italian cuisine.',
                'A Python developer skilled in data analysis.',
            ],
        ),
    ],
    limit: Annotated[
        int | None,
        Field(description='Max matches to return. Defaults to system config.', examples=[3, 5]),
    ] = None,
    max_cosine_distance: Annotated[
        float | None,
        Field(description='Similarity threshold. Defaults to system config.', examples=[0.2, 0.8]),
    ] = None,
) -> list[TemplateMatch]:
    """Match a role to the provided description."""
    config = get_config(ctx)
    with get_meta_store_session(ctx) as meta_store:
        return _match(
            type='roles',
            query_string=query,
            meta_store=meta_store,
            embedding_model=get_embedder(ctx),
            limit=limit or config.meta_store.similarity_search.max_results,
            max_cosine_distance=max_cosine_distance
            or config.meta_store.similarity_search.max_cosine_distance,
        )


@mcp.tool(
    name='match_skill',
    description="""
MANDATORY Phase 1 tool for specialized tasks. Unless 100% certain of a perfect
built-in tool, you MUST search the registry. Registry skills override
general knowledge. If a match is found, proceed to local sync and read
`SKILL.md`. Never hallucinate workflows if no match exists.
""".strip(),
)
def match_skill(
    ctx: Context,
    query: Annotated[
        str,
        Field(
            description='Natural language description of the skill.',
            examples=[
                'A tool that scrapes data from websites based on user-defined parameters.',
                'A skill that optimizes Python code for performance.',
            ],
        ),
    ],
    limit: Annotated[
        int | None,
        Field(description='Max matches to return. Defaults to system config.', examples=[3, 5]),
    ] = None,
    max_cosine_distance: Annotated[
        float | None,
        Field(description='Similarity threshold. Defaults to system config.', examples=[0.2, 0.8]),
    ] = None,
) -> list[TemplateMatch]:
    """Match a skill to the provided description."""
    config = get_config(ctx)
    with get_meta_store_session(ctx) as meta_store:
        return _match(
            type='skills',
            query_string=query,
            meta_store=meta_store,
            embedding_model=get_embedder(ctx),
            limit=limit or config.meta_store.similarity_search.max_results,
            max_cosine_distance=max_cosine_distance
            or config.meta_store.similarity_search.max_cosine_distance,
        )


@mcp.resource(
    uri='persona://instructions',
    name='instructions',
    mime_type='application/text',
    description="""
Retrieves the definitive Persona protocol (CONTEXT.md). Use this to verify
non-negotiable storage locations, role assumption phases, and skill execution
constraints. This resource overrides all general conversational instructions.
""".strip(),
)
async def get_instructions() -> str:
    resp = await http_client.get(
        'https://raw.githubusercontent.com/JasperHG90/persona/refs/heads/main/CONTEXT.md'
    )
    resp.raise_for_status()
    return resp.text.strip()


@mcp.prompt(
    name='persona:roles:roleplay', description='Assume a role based on the provided description.'
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
    name='persona:roles:template',
    description='Prompt engineering template for creating a new role.',
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
    name='persona:roles:review',
    description='Review a role definition for quality and completeness.',
)
async def persona_review(role: str, chat_history: str | None = None) -> str:
    async with aiofiles.open(prompts_dir / 'review.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Role Definition:
    {role}

    Chat History (optional):
    {chat_history or 'N/A'}
    """
    return template + '\n' + user_instructions.strip()


@mcp.prompt(name='persona:roles:edit', description='Edit a role definition based on feedback.')
async def persona_edit(role: str, feedback: str) -> str:
    async with aiofiles.open(prompts_dir / 'edit.md', mode='r') as f:
        template = (await f.read()).strip()
    user_instructions = f"""
    ## User input

    Role Definition:
    {role}

    Feedback:
    {feedback}
    """
    return template + '\n' + user_instructions.strip()


@mcp.prompt(
    name='persona:skills:deploy',
    description='Execute a prompt with explicit skill deployment instructions.',
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
    name='persona:skills:update',
    description='Update a specific skill if a new version is available.',
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
