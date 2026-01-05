# How to Manage Persona Skills

This guide explains how to manage skills in your Persona registry and how to use them in your local projects.

## What is a Skill?

In Persona, a **Skill** is a specialized directory containing instructions (`SKILL.md`), scripts, and resources that help an LLM perform a specific task. Unlike Roles, which define *who* the AI is, Skills define *what* the AI can do and *how* to do it.

## Managing Your Registry

You can manage your global registry of skills using the Persona CLI.

### Listing Skills

To see all skills currently registered in your library:

```bash
persona skills list
```

### Searching for Skills

To find a skill based on its description:

```bash
persona skills match "a skill for analyzing python code"
```

### Registering a New Skill

If you have developed a new skill locally, you can add it to your global registry:

```bash
persona skills register /path/to/your/skill_directory
```

### Removing a Skill

To remove a skill from the registry:

```bash
persona skills remove skill_name
```

## Using Skills in a Project

Skills are designed to be "installed" into a local project's `.persona/skills/` directory.

### Installing a Skill Manually

You can use the CLI to install a skill into your current workspace:

```bash
persona skills install skill_name .persona/skills
```

### Automated Installation (via AI)

When using the Persona MCP server, the AI can automatically discover and install skills for you. When you give the AI a task that matches a skill's description:

1.  The AI calls `match_skill`.
2.  If a match is found, it calls `install_skill`.
3.  The skill is saved to `.persona/skills/<skill_name>`.

## Understanding the Skill Structure

Every installed skill follows a specific structure:

*   **`SKILL.md`:** The "brain" of the skill. It contains the instructions and workflow for the AI.
*   **`scripts/`:** (Optional) Python or shell scripts that the AI can execute to perform the task.
*   **`assets/`:** (Optional) Any additional data files or resources needed by the skill.

## Skill Versioning and Updates

Persona uses unique identifiers (UUIDs) to manage skill versions in the registry.

### Automatic Updates (via AI)

Updating skills is primarily handled by the AI when using the MCP server. When an AI detects that a skill is being used, it can check the registry for a newer version. If a newer version exists (indicated by a change in the skill's metadata), the AI can re-run the `install_skill` tool to update your local files.

### Manual Re-installation

If you want to manually update a skill in your project, simply run the install command again:

```bash
persona skills install skill_name .persona/skills
```

## Best Practices

1.  **Read the `SKILL.md`:** After a skill is installed, the AI is instructed to read the `SKILL.md` file. Ensure your custom skills have clear, concise instructions.
2.  **Keep it Local:** Always install skills into the `.persona/skills/` directory of your project to keep your project environment isolated and reproducible.
3.  **Registry First:** Always register your skills in the Persona registry before trying to use them via the MCP server.
4.  **Use Descriptive Names:** Give your skills clear, descriptive names and summaries to ensure high accuracy during similarity searches.
