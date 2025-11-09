# Quickstart: Manage Personas and Skills

This guide gets you started with the Persona CLI, showing you how to manage personas and skills, and how to run the MCP server for remote access.

## Managing Personas

Personas define the identity of your LLM. You can register new ones from a local file, list the ones you have, and remove them when they're no longer needed.

### Register a new persona

To add a new persona, you need a source file (e.g., `my-persona.yaml`) that defines its properties. Use the `register` command to add it to your library.

```sh
persona register --name "my-awesome-persona" --path /path/to/my-persona.yaml
```

I find it useful to keep all my persona definitions in a dedicated directory to keep things organized.

### List available personas

Once you have a few personas, you can see all of them with the `list` command.

```sh
persona list
```

This gives you a clean table with the name, path, description, and UUID of each persona, so you can quickly see what's available.

### Remove a persona

If you want to remove a persona, just use the `remove` command with its name.

```sh
persona remove "my-awesome-persona"
```

## Managing Skills

Skills are the capabilities you give to your LLM. Just like with personas, you can register, list, and remove them.

### Register a new skill

You can register a new skill from a source file, just like you do with personas.

```sh
skill register --name "my-new-skill" --path /path/to/my-skill.py
```

### List available skills

To see all the skills you've registered, use the `list` command.

```sh
skill list
```

### Remove a skill

To get rid of a skill you no longer need, use the `remove` command.

```sh
skill remove "my-new-skill"
```

## Working with the MCP Server

The MCP (Master Control Program) server exposes a remote API, allowing you to interact with your personas and skills from anywhere.

### Start the server

To get the server running, just use the `start` command.

```sh
mcp start
```

This will start the server on your local machine, and you'll see the log output in your terminal. Now you can send requests to it to manage your LLM resources remotely.
