# Using the Interactive TUI

Persona includes a Terminal User Interface (TUI) for users who prefer a more visual way to browse and manage their registry.

## Launching the TUI

To start the TUI, run the following command in your terminal:

```bash
persona tui
```

## Interface Overview

The TUI is divided into two main tabs: **Roles** and **Skills**.

### 1. Navigation
*   **Tabs:** Use your mouse or arrow keys to switch between the "Roles" and "Skills" tabs at the top.
*   **Keyboard Bindings:**
    *   `q`: Quit the application.
    *   `Tab`: Move focus between widgets (Search, Table, Action Button).

### 2. Searching and Filtering
At the top of each tab is a search bar. As you type, the table below will automatically filter the available templates using semantic search (if embeddings are configured) or simple listing.

### 3. Browsing Details
*   Select a row in the **DataTable** to view the full definition of that role or skill.
*   The **Right Pane** displays a Markdown-rendered preview of the `ROLE.md` or `SKILL.md` file.

## Performing Actions

The TUI allows you to quickly move definitions from your registry to your project.

### Saving a Role
1.  Select a role from the list.
2.  Click the **Save Role** button at the bottom right.
3.  A modal will appear asking for a destination path. Enter the path where you want to save the `ROLE.md` file.

### Installing a Skill
1.  Select a skill from the list.
2.  Click the **Install Skill** button.
3.  Enter the absolute path to the directory where you want the skill to be installed (e.g., `./.persona/skills/my_skill`).
4.  Persona will copy all required files and scripts to that directory.

## Troubleshooting

*   **Empty Lists:** If you don't see any roles or skills, ensure you have run `persona reindex` at least once to populate the metadata store.
*   **Permissions:** Ensure the TUI has write permissions for the directories where you are attempting to save or install templates.
