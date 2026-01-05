import typer

app = typer.Typer(
    name='mcp',
    help='Run and manage the MCP server.',
    no_args_is_help=True,
)


@app.callback()
def main():
    """NB: the MCP app only has a single command, so typer will ignore the command group itself.
    By adding a callback, we ensure that the help text for the command group is still shown."""
    pass


@app.command(name='start')
def start_server():
    """Start the MCP server."""
    try:
        from persona.mcp.server import entrypoint

        _has_mcp_deps = True
    except ImportError:
        _has_mcp_deps = False

    if not _has_mcp_deps:
        typer.echo(
            '[red][bold]MCP dependencies are not installed. Please install Persona with the "mcp" extra.[/bold][/red]'
        )
        raise typer.Exit(code=1)
    else:
        entrypoint()  # type: ignore
