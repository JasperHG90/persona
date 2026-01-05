import typer
import pathlib as plb
from typing import Annotated
from rich.console import Console

from persona.cli.utils import create_cli
from persona.storage import get_file_store_backend, get_meta_store_backend

console = Console()

app = create_cli(
    name='roles',
    template_type='roles',
    help_string='Manage LLM roles.',
    description_string='roles',
)


@app.command(name='get', help='Get the definition of a role.')
def get_role(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(
            help='The name of the role to retrieve.',
        ),
    ],
    output_dir: Annotated[
        plb.Path | None,
        typer.Option(
            '--output-dir',
            '-o',
            help='Directory to save the role definition to. If not provided, prints to console.',
            dir_okay=True,
            file_okay=False,
            writable=True,
        ),
    ] = None,
):
    """Get the definition of a role.

    Args:
        ctx (typer.Context): Typer context
        name (str): The name of the role to retrieve.
    """
    config = ctx.obj['config']
    file_store = get_file_store_backend(config.file_store)
    meta_store = get_meta_store_backend(config.meta_store, read_only=True)

    with meta_store.open(bootstrap=True) as connected:
        with connected.session() as session:
            if not session.exists('roles', name):
                console.print(f'[red]Role "{name}" does not exist.[/red]')
                raise typer.Exit(code=1)
    template_key = 'roles/%s/ROLE.md' % (name)
    role_definition = file_store.load(template_key).decode('utf-8')
    if output_dir:
        output_path = output_dir / name / 'ROLE.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(role_definition, encoding='utf-8')
        console.print(f'[green]Role definition saved to {output_path}[/green]')
    else:
        console.print(role_definition)
