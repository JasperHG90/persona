# Gemini Project Context: Persona

This document provides a high-level overview of the Persona project, its architecture, and key components. It is intended to be a living document that is updated as the project evolves.

## 1. Project Mission & Philosophy

Persona is a Python CLI and MCP (Model Context Protocol) server designed to manage LLM personas and skills on various local and remote storage backends. The project aims to provide a flexible and extensible platform for developers to build and manage their own LLM-powered applications.

## 2. Current Status

The project is under active development. The core functionalities of the CLI and MCP server are in place, and the focus is on adding new features and improving the existing codebase.

## 3. How to Contribute

Currently, there are no formal contribution guidelines. However, the project is open to contributions. If you are interested in contributing, please open an issue on the project's GitHub repository to discuss your ideas.

## 4. Architecture Overview

The project follows a modular architecture, composed of two main components:

*   **CLI:** A command-line interface built with Typer for managing personas and skills (registering, listing, removing).
*   **MCP Server:** A `fastmcp`-based server that exposes a remote API for interacting with personas and skills.

It utilizes a storage abstraction layer (`fsspec`) to interact with different storage backends (currently local storage is implemented).

## 5. Key Technologies & Rationale

*   **Programming Language:** Python 3.12
*   **CLI Framework:** Typer (Chosen for its ease of use and automatic help generation)
*   **Web Framework (MCP):** fastmcp (Chosen for its high performance and async capabilities)
*   **Dependency Management:** uv
*   **Testing:** pytest
*   **Linting/Formatting:** ruff, pre-commit
*   **Containerization:** Docker

Dependencies are managed in `pyproject.toml`.

## 6. Developer Workflow

The `justfile` provides several common commands for development and deployment:

*   `just setup`: Sets up the development environment.
*   `just test`: Runs the test suite.
*   `just pre_commit`: Runs pre-commit checks on all files.
*   `just build_mcp`: Builds the MCP server Docker image.
*   `just push_mcp`: Pushes the MCP server Docker image to the registry.
*   `just deploy_mcp`: Deploys the MCP server to Cloud Run.

## 7. Project Conventions & Quality Gates

The project uses `ruff` for linting and formatting, and `pre-commit` to enforce quality gates before committing code. These checks are also run in the CI pipeline to ensure code quality and consistency.
