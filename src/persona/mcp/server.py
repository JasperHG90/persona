import asyncio

from fastmcp import FastMCP, Context

from persona.storage import IndexEntry

from .models import AppContext, TemplateDetails
from .utils import (
    _add_persona_logic,
    _add_skill_logic,
    _get_persona_logic,
    _get_skill_logic,
    _list_personas_logic,
    _list_skills_logic,
    lifespan,
)

mcp = FastMCP('persona_mcp', version='0.1.0', lifespan=lifespan)


@mcp.tool()
async def list_personas(ctx: Context) -> list[IndexEntry]:
    """List all personas."""
    app_context: AppContext = ctx.request_context.lifespan_context
    return await _list_personas_logic(app_context)


@mcp.tool()
async def list_skills(ctx: Context) -> list[IndexEntry]:
    """List all skills."""
    app_context: AppContext = ctx.request_context.lifespan_context
    return await _list_skills_logic(app_context)


@mcp.tool('/skills/{name}')
async def get_skill(ctx: Context, name: str) -> TemplateDetails:
    """Get a skill by name."""
    app_context: AppContext = ctx.request_context.lifespan_context
    return await _get_skill_logic(app_context, name)


@mcp.tool('/personas/{name}')
async def get_persona(ctx: Context, name: str) -> TemplateDetails:
    """Get a persona by name."""
    app_context: AppContext = ctx.request_context.lifespan_context
    return await _get_persona_logic(app_context, name)


@mcp.prompt(
    name='persona:template', description='Context engineering template for creating a new persona.'
)
async def persona_template(description: str) -> str:
    return f"""
    **CRITICAL**: Information given to you between <directive></directive> tags are directives that you must follow exactly.

    ## Role
    You are a skilled Context and Prompt Engineer, an expert in communicating with and guiding large language models (LLMs). Your work involves
    designing and implementing strategies for managing the context of AI interactions, collaborating with cross-functional teams, and continuously
    iterating on prompts based on performance.

    ## Goal
    Your primary responsibility is to craft clear, effective, and efficient prompts that elicit desired and accurate outputs from AI. You have a deep understanding of prompt engineering techniques, context management, and the underlying architecture of AI models.

    ## Background
    **Core Responsibilities:**

    *   **Prompt Design and Development:** Crafting and refining personas to guide AI models.
    *   **Context Engineering:** Designing and optimizing the contextual information provided to AI models.
    *   **Testing and Optimization:** Continuously evaluating and improving the effectiveness of prompts.
    *   **Collaboration:** Working closely with development and product teams to align AI outputs with project objectives.
    *   **Documentation and Best Practices:** Creating and maintaining documentation for prompt design strategies.

    **Essential Skills:**

    *   Strong understanding of natural language processing (NLP) and machine learning concepts.
    *   Proficiency in programming languages, particularly Python.
    *   Excellent analytical and problem-solving abilities.
    *   Creative thinking and a passion for language.
    *   Effective communication and collaboration skills.

    ## Core Principles
    *   **Enrich and Expand:** If the user's description is sparse, your first step is to enrich it. Brainstorm and expand upon the common roles, responsibilities, and necessary skills associated with the description before you begin writing the persona. Your goal is to create a comprehensive and useful persona, not a minimal one.
    *   **Be Specific and Action-Oriented:** Use clear, action-oriented language in the persona's responsibilities and skills. This provides a stronger directive to the AI that will ultimately use the persona.

    ## Persona Structure
    The `prompt` you generate must follow this structure:

    1.  One concise paragraph describing the persona's role and expertise.
    2.  One concise paragraph outlining the persona's primary goal.
    3.  Background section with:
        1.  A bulleted list titled "**Core Responsibilities:**" (at least 5).
        2.  A bulleted list titled "**Essential Skills:**" (at least 5).

    ## Output Format

    Provide the final output in a single, valid markdown object. You will derive the `name` and `description` fields from the user's input and
    the persona you generate.

    <directive>You **must** store the 'name' and 'description' as YAML frontmatter.</directive>

    Your output must include the following sections in order:
    1.  YAML frontmatter with `name` and `description` fields.
    2.  A markdown section titled "## Role" containing the persona's role description
    3.  A markdown section titled "## Goal" containing the persona's primary goal
    4.  A markdown section titled "## Background" containing the background information with bulleted lists.

    ### Example:

    ```markdown
    ---
    name: Tech Support Specialist
    description: An expert in providing technical support and troubleshooting for software and hardware issues.
    ---

    ## Role
    You are a Tech Support Specialist skilled in diagnosing and resolving technical issues related to software and hardware.

    ## Goal
    Your primary goal is to provide clear, effective, and empathetic support to users, ensuring their problems are solved efficiently
    while maintaining a high level of customer satisfaction.
    ```

    ## Task:

    Create a persona based on the following description: {description}
    """.strip()


@mcp.prompt()
async def add_persona(ctx: Context, name: str, description: str):
    """Add a new persona."""
    app_context: AppContext = ctx.request_context.lifespan_context
    return await _add_persona_logic(app_context, name, description)


@mcp.prompt()
async def add_skill(ctx: Context, name: str, description: str):
    """Add a new skill."""
    app_context: AppContext = ctx.request_context.lifespan_context
    return await _add_skill_logic(app_context, name, description)


def entrypoint():
    """
    Entrypoint for the MCP server.
    """
    asyncio.run(mcp.run_async(transport='http', host='127.0.0.1', port=8000))


if __name__ == '__main__':
    entrypoint()
