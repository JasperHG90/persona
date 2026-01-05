# CLI Reference

This document provides a comprehensive reference for the Persona command-line interface.

## Global Options

These options can be used with any Persona command.

*   `--debug`, `-d`: Enable debug logging.
*   `--config`, `-c FILE`: Path to the configuration file. (Env: `PERSONA_CONFIG_PATH`, Default: `~/.persona.config.yaml`).
*   `--set`, `-s KEY=VALUE`: Override a configuration value (e.g., `-s root=/tmp/persona`). Supports dot notation for nested keys.

## General Commands

*   `init`: Initialize Persona storage and configuration.
*   `reindex`: Re-scan and re-index all roles and skills in the root directory.
*   `tui`: Start the interactive Terminal User Interface.

---

## `roles` Commands

Manage LLM roles (persona definitions).

*   `roles list`: List all available roles in your registry.
*   `roles register [PATH]`: Register a new role from a local directory.
    *   `--github-url`, `-g`: Register from a GitHub repository (format: `https://github.com/<USER>/<REPO>/tree/<BRANCH>`).
    *   `--tag`, `-t`: Add manual tags (repeatable).
    *   `--name`: Override name from frontmatter.
    *   `--description`: Override description from frontmatter.
*   `roles remove [NAME]`: Remove a role from the registry.
*   `roles match [QUERY]`: Search the registry for roles matching a natural language description.
*   `roles get [NAME]`: Retrieve and display the definition of a specific role.
    *   `--output-dir`, `-o`: Save the definition to a directory instead of printing to console.

## `skills` Commands

Manage LLM skills (instruction sets and tools).

*   `skills list`: List all available skills in your registry.
*   `skills register [PATH]`: Register a new skill from a local directory.
    *   `--github-url`, `-g`: Register from a GitHub repository.
    *   `--tag`, `-t`: Add manual tags (repeatable).
    *   `--name`: Override name from frontmatter.
    *   `--description`: Override description from frontmatter.
*   `skills remove [NAME]`: Remove a skill from the registry.
*   `skills match [QUERY]`: Search the registry for skills matching a natural language description.
*   `skills get [NAME]`: Retrieve and display the definition (SKILL.md) of a specific skill.
    *   `--output-dir`, `-o`: Save the definition to a directory instead of printing to console.
*   `skills install [NAME] [OUTPUT_DIR]`: Install a skill's files to a local project directory.

---

## `mcp` Commands

Manage the Model Context Protocol server.

*   `mcp start`: Start the MCP server using the stdio transport.

---

## `config` Commands

Inspect current configuration settings.

*   `config root_dir`: Print the normalized root directory path.
*   `config data_dir`: Print the default user data directory path.
*   `config cache_dir`: Print the default user cache directory path.

---

## `cache` Commands

Manage Persona's local cache (e.g., downloaded models).

*   `cache dir`: Print the path to the cache directory.
*   `cache clean`: Remove all files in the cache directory.
