import pathlib as plb

import typer
from rich.console import Console
from rich.table import Table

from persona.config import PersonaConfig
from persona.api import PersonaAPI

console = Console()


def match_query(ctx: typer.Context, query: str, type: str):
    """Match a query based on the description of a template

    Args:
        ctx (typer.Context): Typer context
        query (str): query string to match
        type (str): type of template to search in
    """
    config: PersonaConfig = ctx.obj['config']
    api = PersonaAPI(config)

    results = api.search_templates(query, type, columns=['name', 'description', 'uuid', 'score'])  # type: ignore

    table = Table('Name', 'Description', 'Distance', 'UUID')

    for result in results:
        table.add_row(
            result['name'],
            result['description'],
            str(round(result['score'], 2)),
            result['uuid'],
        )
    console.print(table)


def list_templates(ctx: typer.Context, type: str):
    """List the templates currently available for a type

    Args:
        ctx (typer.Context): Typer context
        type (str): type of template to list
    """
    config: PersonaConfig = ctx.obj['config']
    api = PersonaAPI(config)
    results = api.list_templates(type, columns=['name', 'description', 'uuid'])  # type: ignore

    table = Table('Name', 'Description', 'UUID')
    for result in results:
        table.add_row(
            result['name'],
            result['description'],
            result['uuid'],
        )
    console.print(table)


def copy_template(
    ctx: typer.Context,
    path: plb.Path,
    name: str | None,
    description: str | None,
    tags: list[str] | None,
    type: str,
):
    """Copy a template from a local path to the target file store.

    Args:
        ctx (typer.Context): Typer context
        path (plb.Path): Path to the template directory
        name (str | None): Name of the template. Defaults to None. If None, then we try to infer it from the template frontmatter.
        description (str | None): Description of the template. Defaults to None. If None, then we try to infer it from the template frontmatter.
        type (str): Type of the template
    """
    config: PersonaConfig = ctx.obj['config']
    api = PersonaAPI(config)
    api.publish_template(path, type, name, description, tags)  # type: ignore


def remove_template(ctx: typer.Context, name: str, type: str):
    """Remove an existing template

    Args:
        ctx (typer.Context): Typer context
        name (str): Name of the template to remove
        type (str): Type of the template to remove

    Raises:
        typer.Exit: If the template does not exist
    """
    config: PersonaConfig = ctx.obj['config']
    api = PersonaAPI(config)

    try:
        api.delete_template(name, type)  # type: ignore
    except ValueError as e:
        console.print(f'[red]{e}[/red]')
        raise typer.Exit(code=1)

    console.print(f'[green]Template "{name}" has been removed.[/green]')


def get_role(
    ctx: typer.Context,
    name: str,
    output_dir: plb.Path | None = None,
):
    """Get a role description and either print it to the console or write it to disk

    Args:
        ctx (typer.Context): Typer context
        name (str): Name of the role to retrieve.
        output_dir (plb.Path | None, optional): Output directory to save the role definition. Defaults to None.

    Raises:
        typer.Exit: If the role does not exist.
    """
    config: PersonaConfig = ctx.obj['config']
    api = PersonaAPI(config)

    try:
        raw_content = api.get_role(name)
    except ValueError as e:
        console.print(f'[red]{e}[/red]')
        raise typer.Exit(code=1)

    if output_dir:
        output_path = output_dir / name / 'ROLE.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(raw_content)
        console.print(f'[green]Role definition saved to {output_path}[/green]')
    else:
        console.print(raw_content.decode('utf-8'))
