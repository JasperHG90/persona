![](./assets/logo.png)

**A developer-friendly toolkit for managing and deploying LLM personas and skills across any environment.**

Persona provides a robust Python CLI and a high-performance MCP server to give you a flexible, extensible platform for your LLM applications. Manage your AI's identity (Roles) and capabilities (Skills), from your local machine to the cloud.

---

## 📚 What is Persona?

Persona is a system designed to standardize how Large Language Models (LLMs) adopt roles and utilize tools.

-   **Roles** are carefully curated prompts that tell the LLM *how* to behave (e.g., "Python Expert", "Master Chef").
-   **Skills** are packages of instructions and scripts that give the LLM the *ability* to perform specific tasks (e.g., "Web Scraper", "Data Analysis").

By decoupling these from your application logic, Persona allows you to:
-   **Standardize** interactions across different LLM providers.
-   **Manage** prompts and tools as code.
-   **Deploy** these capabilities via a standardized MCP server.

### Philosophy

Persona is built on the belief that **prompt engineering is software engineering**. The "who" (Role) and the "how" (Skills) of an AI should be decoupled from the application logic.

*   **Standardization:** Managing personas and skills as consistent, versioned artifacts (code) rather than scattered strings.
*   **Extensibility:** Storing these resources anywhere (local files, cloud storage) via a robust abstraction layer.
*   **Remote Management:** Separating the "brain" management from the client application via a standardized API (MCP).

---

## 🚀 Getting Started

Follow this guide to get Persona up and running on your local machine in minutes.

### 1. Installation

Clone the repository and set up the environment.

```sh
git clone https://github.com/your-repo/persona.git
cd persona
# Uses 'uv' for dependency management
just setup
```

### 2. Initialization

Before using Persona, initialize the configuration and local storage directories. This will create a `.persona` folder in your user data directory (or configured root) to store roles and skills.

```sh
persona init
```

### 3. Verify Installation

Run the test suite to ensure everything is working correctly.

```sh
just test
```

---

## 📖 How-To Guides

### Manage Roles

Roles define the personality and expertise of your LLM.

**List available roles:**
```sh
persona roles list
```

**Register a new role from a local file:**
```sh
persona roles register /path/to/my-role.yaml
```

**Register a role from GitHub:**
```sh
persona roles register path/to/role.yaml --github-url https://github.com/user/repo/tree/main
```

**Match a role based on a description:**
```sh
persona roles match "Expert Python programmer"
```

### Manage Skills

Skills provide executable capabilities to your LLM.

**List available skills:**
```sh
persona skills list
```

**Register a new skill:**
```sh
persona skills register /path/to/skill-directory
```

### Run the MCP Server

The MCP server allows external applications (like Gemini, Claude, or IDE extensions) to interact with your Persona registry.

**Start the server (Stdio mode):**
```sh
persona mcp start
```

**Run via Docker:**
```sh
# Build the image
just build_mcp

# Run the container
docker run \
    -v ~/.persona:/app/.persona \
    -e PERSONA_STORAGE_ROOT=/app/.persona \
    -e PERSONA_STORAGE_TYPE=local \
    persona mcp start
```

---

## ⚙️ Configuration Reference

Persona is configured via a `config.yaml` file (usually in `~/.persona/config.yaml`) or environment variables.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PERSONA_ROOT` | Root directory for file storage. | User data dir (e.g. `~/.local/share/persona`) |
| `PERSONA_FILE_STORE__TYPE` | Storage backend type. | `local` |
| `PERSONA_META_STORE__TYPE` | Metadata/Index backend type. | `duckdb` |
| `PERSONA_LOG_LEVEL` | Logging verbosity. | `INFO` |

### MCP Client Configuration

To use Persona with an MCP client (like Gemini), add this to your client's settings file (e.g., `.gemini/settings.json`):

```json
{
    "mcpServers": {
        "persona": {
            "command": "uv",
            "args": [
                "run",
                "persona",
                "mcp",
                "start"
            ],
            "trusted": true
        }
    }
}
```

---

## 🛠️ Developer Workflow

We use `just` to manage development tasks.

-   `just setup`: Install dependencies and pre-commit hooks.
-   `just test`: Run the full test suite.
-   `just pre_commit`: Run linting and formatting checks.
-   `just build_mcp`: Build the Docker image.

---

## Contributing

We welcome contributions! Please open an issue on GitHub to discuss your ideas before submitting a Pull Request.

## License

This project is licensed under the [MIT License](./LICENSE.txt).
