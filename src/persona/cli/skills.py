import typer
import pathlib as plb
from typing import Annotated

from persona.cli.utils import create_cli
from persona.cli.commands import install_skill


app = create_cli(
    name='skills',
    template_type='skills',
    help_string='Manage LLM skills.',
    description_string='skills',
)


@app.command(name='install', help='Install a skill to a local directory.')
def install_item(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(
            help='The name of the skill to install.',
        ),
    ],
    output_dir: Annotated[
        plb.Path,
        typer.Argument(
            help='Directory to save the skill to.',
            dir_okay=True,
            file_okay=False,
            writable=True,
            resolve_path=True,
        ),
    ],
):
    """Get the definition of a role.

    Args:
        ctx (typer.Context): Typer context
        name (str): The name of the role to retrieve.
    """
    install_skill(ctx, name, output_dir)
