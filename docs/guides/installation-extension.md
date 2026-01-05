# How to Install the Gemini Persona Extension

This guide explains how to install the Persona extension for the Gemini CLI and llxprt, enabling you to use Persona's roles and skills directly within your Gemini chats.

## Prerequisites

- You have installed the Gemini CLI or llxprt.
- You have installed Persona using as e.g. a `uv` tool.
- You have initialized Persona using `persona init`.

## Installation Steps

### 1. Install the Extension

You can install the Persona extension directly from its GitHub repository using the Gemini CLI:

```bash
gemini extension install https://github.com/JasperHG90/persona
```

Gemini will automatically configure the Persona MCP server.

### 2. Verify the Installation

To verify that the extension and MCP server are working correctly:

1.  Start a new chat with Gemini:
    ```bash
    gemini chat
    ```
2.  Check if the Persona tools are available. You can ask Gemini:
    ```text
    What Persona tools do you have access to?
    ```
    Gemini should list tools like `match_role`, `get_role`, `match_skill`, and `install_skill`.

## Using Persona in Gemini

Once installed, you can trigger Persona workflows using natural language:

*   **To adopt a role:** "Act as a Python expert."
*   **To find a skill:** "Do you have a skill for scraping websites?"

Gemini will automatically use the Persona MCP tools to find, install, and assume the requested roles or skills.
