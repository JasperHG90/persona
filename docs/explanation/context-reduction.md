# Context Reduction Strategies

This document explains the philosophy and techniques for managing the context window when using Persona.

## The Problem: Context Bloat

When working with LLMs, the "context window" (the amount of text the model can process at once) is a precious resource. Filling it with unnecessary information leads to:

*   **Higher Costs:** More tokens mean more money.
*   **Slower Responses:** Processing large contexts takes longer.
*   **Reduced Accuracy:** Models can get "distracted" by irrelevant details (the "needle in a haystack" problem).

## The Persona Solution: Just-in-Time Context

Persona is designed to solve this by treating Roles and Skills as **dynamic modules** rather than static system prompts.

### 1. The "Push Down" Strategy

Instead of loading *every* possible role and skill into the system prompt at the start of a chat, Persona encourages a "Push Down" strategy:

*   **Start Light:** Your initial `CONTEXT.md` should only contain the core instructions on *how* to use Persona (search, install, assume).
*   **Load on Demand:** The AI only loads a specific Role or Skill when the user explicitly requests it or when the task requires it.
*   **Unload (Conceptually):** While the files remain in `.persona/`, the AI focuses on the *active* role.

### 2. Managing the `.persona` Directory

The `.persona/` directory acts as a local cache. To keep context efficient:

*   **Pruning:** Periodically remove unused skills from `.persona/skills/`. If the AI scans the directory and sees 50 skills, that consumes context.
*   **Selective Installation:** Don't install the entire registry. Only install what you need for the current project.

### 3. Optimized Role Definitions

When creating Roles:

*   **Be Concise:** Focus on *directives* and *behavior* rather than long backstories, unless the backstory is essential for the persona's tone. Use the `persona:roles:template` prompt to generate a starting point. Use `persona:roles:review` and `persona:roles:edit` to update prompts based on a chat history or feedback.
*   **Link to Skills:** Instead of writing long procedures inside a Role, create a separate Skill. The Role can then simply "know" to use that Skill.

## Summary

Effective context reduction involves a shift in mindset: **Don't teach the AI everything at once. Teach it how to find what it needs.**
