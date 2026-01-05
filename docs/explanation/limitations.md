# Known Limitations

While Persona is a powerful tool for managing AI personas, there are several architectural and operational limitations to be aware of.

## 1. Single-Writer Constraint

Persona uses **DuckDB** for its metadata store and **SQLite** (via DuckDB) for internal session management. These databases are generally optimized for single-writer access.

*   **Impact:** Running multiple CLI commands or MCP servers that attempt to write to the same metadata store simultaneously may result in "database locked" errors.
*   **Recommendation:** Ensure only one process is performing indexing or registration tasks at a time.

## 2. Local Execution Environment

The Persona MCP server is designed to interact with the **local filesystem** of the machine where the LLM's client (e.g., VS Code, Claude Desktop) is running.

*   **Impact:** If you run the MCP server in a remote container or cloud environment without proper volume mounting, it will not be able to write `.persona/skills` or `.persona/roles` to your local project directory.
*   **Recommendation:** Use Persona in environments where the AI has direct (or proxied) access to the workspace filesystem.

## 3. Python and `uv` Dependency

Many built-in and registry skills rely on Python scripts with inline dependencies (PEP 723).

*   **Impact:** To use these skills, the host machine **must** have Python and `uv` installed. The AI is instructed to use `uv run`, and failure to have these tools will cause skill execution to fail.
*   **Recommendation:** Ensure `uv` is in your system PATH.

## 4. Storage Backend Support

The `PersonaConfig` and `PersonaAPI` are designed to be extensible, but current implementations focus on the **Local File Store**.

*   **Impact:** While `BaseFileStore` allows for S3 or GCS backends in theory, the configuration and TUI are currently optimized for local path management.
*   **Recommendation:** Use the default local storage for the most stable experience.

## 5. Context Window Size

Persona helps reduce context bloat, but it does not eliminate it.

*   **Impact:** Installing too many skills or using extremely long role definitions can still exhaust the context window of smaller models.
*   **Recommendation:** Follow the [Context Reduction](./context-reduction.md) strategies.
