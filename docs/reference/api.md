# API Integration

This document explains how to integrate Persona into your applications, either as a Python library or via its MCP server.

## Overview

Persona is designed as a **Library and Registry** for LLM capabilities. It does not serve an OpenAI-compatible API for model completions itself. Instead, it provides a structured way to retrieve the right prompts (Roles) and tools (Skills) to *send* to an OpenAI-compatible model.

## Integration Methods

1.  **MCP Server (Recommended):** The easiest way to use Persona with LLMs. Connect any MCP-compatible client to the Persona server.
2.  **Python API:** Use the `PersonaAPI` class directly in your Python applications to programmatically manage and retrieve roles and skills.

---

## Python API Reference

If you are building a custom application, you can use the `PersonaAPI` to interact with your Persona library.

### Initialization

```python
from persona.config import PersonaConfig
from persona.api import PersonaAPI
from persona.storage import get_file_store_backend, get_meta_store_backend
from persona.embedder import get_embedding_model

# Load configuration
config = PersonaConfig()

# Initialize backends
file_store = get_file_store_backend(config.file_store)
meta_store = get_meta_store_backend(config.meta_store)

# Initialize API
with meta_store.open(bootstrap=True) as connected_meta:
    api = PersonaAPI(
        config=config,
        file_store=file_store,
        meta_store=connected_meta,
        embedder=get_embedding_model()
    )

    # Use the API...
```

### Common Operations

#### Searching for a Role

```python
results = api.search_templates(
    query="Expert Python Developer",
    type="roles",
    columns=["name", "description", "uuid"]
)
```

#### Retrieving a Role Definition

```python
content = api.get_definition(name="python_expert", type="roles")
print(content.decode("utf-8"))
```

#### Installing a Skill Locally

```python
from pathlib import Path

api.install_skill(
    name="web_scraper",
    local_skill_dir=Path("./.persona/skills")
)
```

---

## Persona and OpenAI-Compatible APIs

While Persona doesn't provide a completion API, it is often used in conjunction with them.

### Typical Workflow

1.  **User Input:** "I need you to act as a security auditor."
2.  **Persona Search:** Your application uses `PersonaAPI` to search for a "Security Auditor" role.
3.  **Prompt Construction:** Your application retrieves the role definition and incorporates it into the prompt context (e.g., as a system instruction or part of the user message, depending on the model's requirements).
4.  **Model Call:** Your application sends the constructed prompt to an OpenAI-compatible API (e.g., OpenAI, Anthropic, or a local server like vLLM).

### Using with MCP

If your AI agent supports MCP (like the Gemini CLI `llxprt`), the agent handles the connection to the OpenAI-compatible API and uses Persona's tools to dynamically augment its own context.
