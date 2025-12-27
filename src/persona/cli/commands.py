import pathlib as plb
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from persona.config import PersonaConfig
from persona.storage import get_file_store_backend, get_meta_store_backend, IndexEntry, Transaction
from persona.templates import TemplateFile, Template
from persona.embedder import get_embedding_model
from persona.types import personaTypes

console = Console()


def match_query(ctx: typer.Context, query: str, type: personaTypes):
    """Match a query based on the description of a template

    Args:
        ctx (typer.Context): Typer context
        query (str): query string to match
        type (personaTypes): type of template to search in
    """
    config: PersonaConfig = ctx.obj['config']
    meta_store = get_meta_store_backend(config.meta_store)
    embedder = get_embedding_model()
    table = Table('Name', 'Path', 'Description', 'Distance', 'UUID')
    query_vector = embedder.encode(query).tolist()
    with meta_store.open(bootstrap=True) as connected:
        with connected.session() as session:
            results = session.search(
                query=query_vector,
                table_name=type,
                limit=config.meta_store.similarity_search.max_results,
                column_filter=['name', 'description', 'uuid', 'score'],
                max_cosine_distance=config.meta_store.similarity_search.max_cosine_distance,
            )
    for result in results.to_pylist():
        table.add_row(
            result['name'],
            '%s/%s/%s' % (config.root, type, result['name']),
            result['description'],
            str(round(result['score'], 2)),
            result['uuid'],
        )
    console.print(table)


def list_templates(ctx: typer.Context, type: personaTypes):
    """List the templates currently available for a type

    Args:
        ctx (typer.Context): Typer context
        type (personaTypes): type of template to list
    """
    config: PersonaConfig = ctx.obj['config']
    meta_store = get_meta_store_backend(config.meta_store)
    table = Table('Name', 'Path', 'Description', 'UUID')
    with meta_store.open(bootstrap=True) as connected:
        with connected.session() as session:
            results = session.get_many(
                table_name=type,
                column_filter=['name', 'description', 'uuid'],
            )
    for result in results.to_pylist():
        table.add_row(
            result['name'],
            '%s/%s/%s' % (config.root, type, result['name']),
            result['description'],
            result['uuid'],
        )
    console.print(table)


def copy_template(
    ctx: typer.Context,
    path: plb.Path,
    name: str | None,
    description: str | None,
    type: personaTypes,
):
    """Copy a template from a local path to the target file store.

    Args:
        ctx (typer.Context): Typer context
        path (plb.Path): Path to the template directory
        name (str | None): Name of the template. Defaults to None. If None, then we try to infer it from the template frontmatter.
        description (str | None): Description of the template. Defaults to None. If None, then we try to infer it from the template frontmatter.
        type (personaTypes): Type of the template
    """
    config: PersonaConfig = ctx.obj['config']
    target_file_store = get_file_store_backend(config.file_store)
    meta_store = get_meta_store_backend(config.meta_store)
    embedder = get_embedding_model()
    template: Template = TemplateFile.validate_python({'path': path, 'type': type})
    with Transaction(target_file_store, meta_store):
        template.process_template(
            entry=IndexEntry(name=name, description=description),
            target_file_store=target_file_store,
            meta_store_engine=meta_store,
            embedder=embedder,
        )


def remove_template(ctx: typer.Context, name: str, type: personaTypes):
    """Remove an existing template

    Args:
        ctx (typer.Context): Typer context
        name (str): Name of the template to remove
        type (personaTypes): Type of the template to remove

    Raises:
        typer.Exit: If the template does not exist
    """
    config: PersonaConfig = ctx.obj['config']
    target_file_store = get_file_store_backend(config.file_store)
    meta_store = get_meta_store_backend(config.meta_store)

    with Transaction(target_file_store, meta_store):
        # NB: connection is re-used later since we've already opened it
        with meta_store.open(bootstrap=True) as connected:
            with connected.session() as session:
                if not session.exists(type, name):
                    console.print(f'[red]{type.capitalize()} "{name}" does not exist.[/red]')
                    raise typer.Exit(code=1)
            template_key = '%s/%s' % (type, name)
            for file in target_file_store.glob('%s/**/*' % template_key):
                if target_file_store.is_dir(file):
                    continue
                file_ = cast(str, file)
                target_file_store.delete(file_)
            # Delete the template directory
            target_file_store.delete(template_key, recursive=True)
            meta_store.deindex(entry=IndexEntry(name=name, type=type))

    console.print(f'[green]Template "{name}" has been removed.[/green]')
