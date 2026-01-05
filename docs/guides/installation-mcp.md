# How to Install Persona MCP in Other Environments

This guide explains how to connect Persona's MCP server to any host application that supports the Model Context Protocol (MCP) using the stdio transport.

## Prerequisites

- You have installed [uv](https://github.com/astral-sh/uv).
- You have initialized Persona using `persona init`.

## Connection Command

The Persona MCP server communicates over `stdio`. Most MCP clients (like IDEs or Desktop assistants) require a command and a set of arguments to launch the server.

### Using `uvx` (Recommended)

The easiest way to run the server without manually managing a virtual environment is using `uvx`:

**Command:** `uvx`
**Arguments:** `--from git+https://github.com/JasperHG90/persona.git persona mcp start`

### Using a local Python Environment

If you have installed Persona into a specific virtual environment:

**Command:** `/path/to/your/venv/bin/persona`
**Arguments:** `mcp start`

## Configuration in MCP Clients

When adding Persona to an MCP-compatible client, you will typically need to add a snippet to the client's configuration file.

### General JSON Configuration

```json
{
  "mcpServers": {
    "persona": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/JasperHG90/persona.git",
        "persona",
        "mcp",
        "start"
      ],
      "env": {
        "PERSONA_ROOT": "/your/custom/root/if/needed"
      }
    }
  }
}
```

## Environment Variables

You can pass environment variables to the MCP server to customize its behavior:

- `PERSONA_ROOT`: Overrides the default data directory.
- `PERSONA_LOG_LEVEL`: Sets the logging verbosity (e.g., `DEBUG`, `INFO`).

## Verification

Once the server is configured in your host application, the application should discover the following tools:

- `match_role`: Search for roles.
- `get_role`: Retrieve role definitions.
- `match_skill`: Search for skills.
- `install_skill`: Install skills to your local workspace.
