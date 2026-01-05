# Built-in Skills and Capabilities

Persona comes with a set of built-in skills and prompts designed to manage the persona lifecycle and ensure the integrity of the registry.

## Built-in Skills

Built-in skills are packaged directly with the Persona library and are available to the AI without requiring external installation.

### `markdown-version-extractor`

This skill is essential for the **Version Sync** phase of the Persona Protocol. It allows the AI to programmatically determine the version or UUID of a local skill by parsing its YAML frontmatter.

*   **Registry Name:** `markdown-version-extractor`
*   **Purpose:** Extract `version` or `uuid` fields from `SKILL.md` or `ROLE.md`.
*   **Key Files:**
    *   `SKILL.md`: The skill definition.
    *   `scripts/get_version.py`: A Python script that performs the extraction using `uv`.
*   **Capabilities:**
    *   Parses YAML frontmatter.
    *   Returns JSON metadata including the version status.
    *   Supports fallback to `version` if `uuid` is missing.

## Built-in MCP Prompts

The Persona MCP server provides several built-in prompts that help you interact with roles and skills effectively.

| Prompt Name | Purpose |
| :--- | :--- |
| `persona:roles:roleplay` | Quickly assume a role based on a natural language description. |
| `persona:roles:template` | Generate a new, high-quality role definition based on user input. |
| `persona:roles:review` | Analyze an existing role definition for quality, consistency, and completeness. |
| `persona:roles:edit` | Iteratively improve a role definition based on specific feedback. |
| `persona:skills:deploy` | Instruct the AI on how to correctly deploy and initialize a skill. |
| `persona:skills:update` | Guide the AI through the process of updating a local skill when a new version is detected. |

## How to List Available Skills

You can view all skills (both built-in and registered) using the following methods:

### Via CLI
```bash
persona list skills
```

### Via MCP Tool
Call the `list_skills` tool from your LLM interface.
