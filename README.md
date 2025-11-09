# Persona

**A developer-friendly toolkit for managing and deploying LLM personas and skills across any environment.**

Persona provides a robust Python CLI and a high-performance MCP (Master Control Program) server to give you a flexible, extensible platform for your LLM applications. Manage your AI's identity and capabilities, from your local machine to the cloud.

## What can you do with Persona?

- **Standardize Personas:** Define and manage consistent personas for your LLM applications.
- **Decouple Skills:** Treat LLM skills as independent, manageable components.
- **Flexible Storage:** Use local filesystems, or extend Persona to support any backend via `fsspec`.
- **Remote Management:** Interact with your personas and skills from anywhere using the `fastmcp`-based server.

## Key Features

- **Command-Line Interface:** A powerful CLI built with Typer for intuitive management of personas and skills.
- **MCP Server:** A high-performance, async-capable server that exposes a remote API.
- **Extensible Storage:** A storage abstraction layer that currently supports local storage, with the flexibility to add more backends.
- **Modern Tech Stack:** Built with Python 3.12, tested with `pytest`, and formatted with `ruff`.

## Getting Started in 5 Minutes

Get the Persona CLI up and running on your local machine.

### 1. Set up the environment

Clone the repository and use the `justfile` to install all dependencies and pre-commit hooks.

```sh
git clone https://github.com/your-repo/persona.git
cd persona
just setup
```

### 2. Run the tests

Verify that everything is set up correctly by running the test suite.

```sh
just test
```

## How to Use the CLI

Ready to dive in? Our [Quickstart Guide](./docs/quickstart.md) walks you through registering, listing, and removing personas and skills, plus how to get the MCP server up and running.

Here are a few examples of how you can use the Persona CLI to manage your resources.

**List all available personas:**
```sh
persona list-personas
```

**Register a new persona from a file:**
```sh
persona register-persona --name "my-persona" --source-file "/path/to/persona.yaml"
```

**List all available skills:**
```sh
persona list-skills
```

## Developer Workflow

The `justfile` contains all the commands you need for development:

- `just setup`: Set up the development environment.
- `just test`: Run the test suite.
- `just pre_commit`: Run pre-commit checks on all files.
- `just build_mcp`: Build the MCP server Docker image.

## Contributing

We're open to contributions! If you have an idea, please open an issue on GitHub to start the discussion.

## License

This project is licensed under the [MIT License](./LICENSE.txt).

## Building and running the dockerfile

Build the dockerfile using e.g.

```shell
docker build -t persona .
```

Run the dockerfile using e.g.

```shell
docker run \
    -v ~/.persona:/app/.persona \
    -e PERSONA_STORAGE_ROOT=/app/.persona \
    -e PERSONA_STORAGE_TYPE=local \
    persona mcp start
```

## Configuring the MCP Server

The `.gemini/settings.json` file configures how Gemini connects to the MCP (Master Control Program) server. This setup allows Gemini to interact with your LLM personas and skills.

Here's the structure of the `settings.json` file:

```json
{
    "mcpServers": {
        "persona": {
            "httpUrl": "http://localhost:8000/mcp",
            "trusted": true
        }
    }
}
```

- **`mcpServers`**: This is a top-level object that holds configurations for different MCP servers.
- **`persona`**: This is the name of the MCP server configuration. You can define multiple servers here.
    - **`httpUrl`**: The URL where the MCP server is running. In this example, it's set to `http://localhost:8000/mcp`.
    - **`trusted`**: A boolean indicating whether the server is trusted. When `true`, Gemini will automatically trust the server's capabilities.
