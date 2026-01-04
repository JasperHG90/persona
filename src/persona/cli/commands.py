import pathlib as plb
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from persona.config import PersonaConfig
from persona.storage import get_file_store_backend, get_meta_store_backend, IndexEntry, Transaction
from persona.templates import TemplateFile, Template
from persona.embedder import get_embedding_model
from persona.tagger import get_tagger
from persona.utils import get_templates_data, search_templates_data

console = Console()


def match_query(ctx: typer.Context, query: str, type: str):
    """Match a query based on the description of a template

    Args:
        ctx (typer.Context): Typer context
        query (str): query string to match
        type (str): type of template to search in
    """
    config: PersonaConfig = ctx.obj['config']
    meta_store = get_meta_store_backend(config.meta_store, read_only=True)
    embedder = get_embedding_model()
    with meta_store.open(bootstrap=True) as connected:
        with connected.read_session() as session:
            results = search_templates_data(
                query,
                embedder,
                session,
                config.root,
                type,
                limit=config.meta_store.similarity_search.max_results,
                max_cosine_distance=config.meta_store.similarity_search.max_cosine_distance,
            )
    table = Table('Name', 'Path', 'Description', 'Distance', 'UUID')

    for result in results:
        table.add_row(
            result['name'],
            result['path'],
            result['description'],
            str(round(result['distance'], 2)),
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
    meta_store = get_meta_store_backend(config.meta_store, read_only=True)
    table = Table('Name', 'Path', 'Description', 'UUID')
    with meta_store.open(bootstrap=True) as connected:
        with connected.session() as session:
            results = get_templates_data(session, config.root, type)
    for result in results:
        table.add_row(
            result['name'],
            result['path'],
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
    target_file_store = get_file_store_backend(config.file_store)
    meta_store = get_meta_store_backend(config.meta_store, read_only=False)
    embedder = get_embedding_model()
    tagger = get_tagger(embedder)
    template: Template = TemplateFile.validate_python({'path': path, 'type': type})
    with Transaction(target_file_store, meta_store):
        template.process_template(
            entry=IndexEntry(name=name, description=description, tags=tags),
            target_file_store=target_file_store,
            meta_store_engine=meta_store,
            embedder=embedder,
            tagger=tagger,
        )


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
    target_file_store = get_file_store_backend(config.file_store)
    meta_store = get_meta_store_backend(config.meta_store, read_only=False)

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
