# How to Manage Persona Context

This guide explains how to use the `CONTEXT.md` file to provide AIs with the necessary instructions and "memory" to use Persona effectively.

## What is `CONTEXT.md`?

`CONTEXT.md` is a specialized file that contains the system prompt for an LLM. It tells the AI how to interact with Persona tools, where to store files, and how to follow specific workflows for roles and skills.

## Initializing Context

The method for initializing context depends on the client you are using.

### 1. Gemini CLI (Automatic)

If you are using the Gemini CLI with the Persona extension installed, **you do not need to do anything**. The extension automatically injects the necessary context from `CONTEXT.md` into your session.

### 2. Other Clients (Claude Desktop, Cline, etc.)

If you are using Persona as a generic MCP server with other clients, the context is not automatically loaded. You have two options:

*   **Manual Injection:** Copy the content of `CONTEXT.md` into your project's system prompt or custom instructions file.
*   **Resource Retrieval:** The Persona MCP server exposes a resource called `persona://instructions`. You can instruct the AI to read this resource at the start of a session to "learn" the Persona protocol.

    *Example prompt:* "Please read the `persona://instructions` resource to understand how to manage roles and skills."

## The Memory Bank Concept

Unlike static instruction files, `CONTEXT.md` in Persona acts as a **Memory Bank**.

### How it Works

When an AI identifies a new role or skill, it doesn't just use it once. It follows a protocol to:

1.  **Search** for the template in the Persona registry.
2.  **Download/Install** the template to a local `.persona/` directory.
3.  **Update** its internal state based on the local files.

### Why use a local `.persona` directory?

Persona enforces a **Strict Storage Protocol**:

*   All roles are stored in `.persona/roles/`.
*   All skills are stored in `.persona/skills/`.

This ensures that the AI's "memory" of a specific project remains contained within that project, making it portable and easy to manage.
