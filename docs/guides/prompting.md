# Prompting Tips for Persona

This guide provides strategies for effectively using natural language to trigger Persona's role and skill workflows.

## How to Trigger Persona

When you are using an AI equipped with the Persona MCP server, you don't need to use specific commands. Instead, you use natural language to describe what you want the AI to "be" (a role) or "do" (a skill).

### 1. Adopting a Role

To trigger a role search, use phrases that describe a persona or a profession.

*   **Explicit:** "Act as a professional Python developer."
*   **Direct:** "Role: Expert Technical Writer."
*   **Descriptive:** "I want you to be a master chef specializing in Japanese cuisine."

**What happens next?**
The AI will search the registry, load the best match, and then enter a **standby state**. It will wait for your next command before acting.

### 2. Deploying a Skill

To trigger a skill search, describe a specialized task that might require specific tools or instructions.

*   **Task-based:** "Scrape the latest news from this website."
*   **Requirement-based:** "Optimize this Python code for performance."
*   **Specialized:** "Help me deploy this application to AWS."

**What happens next?**
The AI will search for a matching skill, install it to your local `.persona/skills/` directory, read the `SKILL.md` instructions, and then proceed with the task.

---

## Best Practices for Prompting

### Be Specific in Your Descriptions

The Persona Meta Store uses similarity search. The more detail you provide, the better the match.

*   **Poor:** "Be a coder."
*   **Better:** "Be a senior backend engineer specializing in FastAPI and PostgreSQL."

### Use Clear Intent

If you want the AI to perform a task *using* a specific skill, mention the task clearly.

*   **Vague:** "Look at this website."
*   **Effective:** "Use a web scraping skill to extract the price of the products on this page."

### Understand the "Standby" State for Roles

When an AI assumes a role, it is instructed **not to speak until spoken to**. This is intentional to prevent the AI from rambling before it has a task.

*   **If the AI goes quiet:** This means it has successfully loaded the role. Give it your first task (e.g., "Review this code" or "Outline this document").

### Creating Roles on the Fly

If Persona can't find a matching role, you can ask the AI to create one for you.

*   **Prompt:** "I need a role for a specialized Terraform auditor. Since you don't have one in the registry, please create a role definition for me and save it to my library."

## Troubleshooting

*   **AI doesn't find a match:** Try rephrasing your description with different keywords.
*   **AI doesn't install the skill:** Ensure your workspace allows the AI to write files to the `.persona/` directory.
*   **AI proceeds with general knowledge instead of a skill:** Explicitly ask: "Search your Persona registry for a skill that can do this."
