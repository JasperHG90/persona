import typer

try:
    from persona.mcp.server import entrypoint

    _has_mcp_deps = True
except ImportError:
    _has_mcp_deps = False

app = typer.Typer()


@app.command(name='start')
def start_server():
    """Start the MCP server."""

    if not _has_mcp_deps:
        typer.echo(
            '[red][bold]MCP dependencies are not installed. Please install Persona with the "mcp" extra.[/bold][/red]'
        )
        raise typer.Exit(code=1)
    else:
        entrypoint()  # type: ignore
