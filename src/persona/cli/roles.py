import typer
import pathlib as plb
from typing import Annotated

from persona.cli.utils import create_cli
from persona.cli.commands import get_role

app = create_cli(
    name='roles',
    template_type='roles',
    help_string='Manage LLM roles.',
    description_string='roles',
)


@app.command(name='get', help='Get the definition of a role.')
def get_item(
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
    get_role(ctx, name, output_dir)
