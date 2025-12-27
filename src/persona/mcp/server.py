import os
import asyncio
from typing import Annotated, cast
import pathlib as plb
import logging

import aiofiles
from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from fastmcp.utilities.logging import configure_logging
from pydantic import Field

from persona.storage import BaseMetaStore, BaseFileStore
from persona.config import PersonaConfig
from persona.embedder import FastEmbedder

from .models import TemplateDetails
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

prompts_dir = plb.Path(__file__).parent / 'prompts'

context_template = (prompts_dir / 'context.md').read_text().strip()

configure_logging(level='DEBUG')

persona_logger = logging.getLogger('persona')
persona_logger.setLevel(os.getenv('PERSONA_LOG_LEVEL', 'INFO'))

mcp = FastMCP('persona_mcp', instructions=context_template, version='0.1.0', lifespan=lifespan)


@mcp.tool(description='List all available roles.')
def list_roles(session=Depends(get_meta_store_session)) -> list[dict]:
    """List all roles."""
    return _list('roles', cast(BaseMetaStore, session))


@mcp.tool(description='List all available skills.')
def list_skills(session=Depends(get_meta_store_session)) -> list[dict]:
    """List all skills."""
    return _list('skills', cast(BaseMetaStore, session))


# NB: this only works if the MCP is running locally so it can write files to disk
@mcp.tool(
    name='install_skill',
    description="""
    RETRIEVAL PROTOCOL:
    1. This tool installs a Skill by installing it to the specified **absolute** local root directory.
    2. The **absolute** local root directory must exist prior to calling this tool.
    3. After installation, the SKILL.md file will be available in <local_skill_dir>/<skill_name>/SKILL.md.
    4. You **MUST** read the SKILL.md file and follow the execution instructions specified there.
    """,
)
def install_skill(
    name: Annotated[str, Field(description='Name of the skill to retrieve.')],
    local_skill_dir: Annotated[
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
    meta_store=Depends(get_meta_store_session),
    file_store: BaseFileStore = Depends(get_file_store),
) -> str:
    """Get a skill by name."""
    return _write_skill_files(
        local_skill_dir, name, meta_store=cast(BaseMetaStore, meta_store), file_store=file_store
    )


@mcp.tool(
    name='get_skill_version',
    description='Get a skill version by name.',
)
def get_skill_version(
    name: Annotated[str, Field(description='Name of the skill to retrieve the version for.')],
    meta_store=Depends(get_meta_store_session),
) -> str:
    """Get a skill version by name."""
    return _get_skill_version(name, cast(BaseMetaStore, meta_store))


@mcp.tool(
    name='get_role',
    description='Get a role by name.',
)
def get_role(
    name: Annotated[str, Field(description='Name of the role to retrieve.')],
    meta_store=Depends(get_meta_store_session),
    file_store: BaseFileStore = Depends(get_file_store),
) -> TemplateDetails:
    """Get a role by name."""
    return _get_persona(name, meta_store=cast(BaseMetaStore, meta_store), file_store=file_store)


@mcp.tool(
    name='match_role',
    description="""Searches the Persona roles registry for relevant roles based
    on a natural language description. Use this tool when users ask for a specific role
    or some natural language description of a prompt.

    EXAMPLES:
    - "You are an expert JavaScript developer who writes clean and efficient code."
    - "Go expert data scientist skilled in Python and machine learning."

    OUTPUT: Returns a list of matching prompt names and their descriptions from the registry
    for matches within the specified cosine distance threshold and a maximum number of results.""",
)
def match_role(
    query: Annotated[
        str, Field(description='Natural language description of the prompt or role needed.')
    ],
    limit: Annotated[
        int | None,
        Field(
            description='Maximum number of results to return. If None, will be taken from configuation file.'
        ),
    ] = None,
    max_cosine_distance: Annotated[
        float | None,
        Field(
            description='Maximum cosine distance threshold for matches. If None, will be taken from configuration file.'
        ),
    ] = None,
    meta_store=Depends(get_meta_store_session),
    embedding_model: FastEmbedder = Depends(get_embedder),
    config: PersonaConfig = Depends(get_config),
) -> list[dict]:
    """Match a role to the provided description."""
    return _match(
        type='roles',
        query_string=query,
        meta_store=cast(BaseMetaStore, meta_store),
        embedding_model=embedding_model,
        config=config,
        limit=limit,
        max_cosine_distance=max_cosine_distance,
    )


@mcp.tool(
    name='match_skill',
    description="""Searches the Persona skills registry for relevant skills or capabilities.
    Use this tool whenever the user asks for a task that you don't have a
    built-in tool for (e.g., 'scrape web', 'optimize code').

    OUTPUT: Returns a list of matching skill names and their descriptions from the registry
    for matches within the specified cosine distance threshold and a maximum number of results.""",
)
def match_skill(
    query: Annotated[
        str, Field(description='Natural language description of the prompt or role needed.')
    ],
    limit: Annotated[
        int | None,
        Field(
            description='Maximum number of results to return. If None, will be taken from configuation file.'
        ),
    ] = None,
    max_cosine_distance: Annotated[
        float | None,
        Field(
            description='Maximum cosine distance threshold for matches. If None, will be taken from configuration file.'
        ),
    ] = None,
    meta_store=Depends(get_meta_store_session),
    embedding_model: FastEmbedder = Depends(get_embedder),
    config: PersonaConfig = Depends(get_config),
) -> list[dict]:
    """Match a skill to the provided description."""
    return _match(
        type='roles',
        query_string=query,
        meta_store=cast(BaseMetaStore, meta_store),
        embedding_model=embedding_model,
        config=config,
        limit=limit,
        max_cosine_distance=max_cosine_distance,
    )


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
