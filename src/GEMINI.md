# Gemini Project Context: `src` Directory

This document provides a specialized context for the `src` directory, which houses the core application source code for the Persona project.

## 1. Role of This Component (`src`)

This directory is the heart of the Persona application. It contains all the Python source code for the `persona` package, which is organized into the following key sub-packages:

*   **`persona.cli`:** Implements the command-line interface.
*   **`persona.mcp`:** Contains the Master Control Program (MCP) server logic.
*   **`persona.storage`:** Provides the storage abstraction layer for interacting with different backends.

## 2. Key Technologies (Component-Specific)

The technologies used within this directory are consistent with the project-wide technologies defined in the root `GEMINI.md`. The primary language is Python 3.12.

## 3. Developer Workflow (Component-Specific)

All development and testing activities for the code in this directory are orchestrated by the `justfile` in the project root. There are no unique workflow commands specific to this directory.

## 4. Mandatory Rules & Conventions (Component-Specific)

*   All code within this directory must adhere to the linting, formatting, and quality gate standards defined in the root `GEMINI.md` and enforced by the project's `pre-commit` configuration.
*   This component inherits all rules from the parent `GEMINI.md`.
