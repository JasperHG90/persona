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
        typer.echo('MCP dependencies are not installed. Please install the required packages.')
        raise typer.Exit(code=1)
    else:
        entrypoint()  # type: ignore
