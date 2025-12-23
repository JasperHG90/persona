import enum
import pathlib as plb
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from persona.config import StorageConfig
from persona.storage import get_storage_backend, IndexEntry, Transaction, VectorDatabase
from persona.templates import TemplateFile, Template

console = Console()


class TemplateTypeEnum(str, enum.Enum):
    PERSONA = 'persona'
    SKILL = 'skill'


def match_query(ctx: typer.Context, query: str, type: TemplateTypeEnum):
    config: StorageConfig = ctx.obj['config']
    db = VectorDatabase(uri=config.root.index_path)
    _type = type.value + 's'
    table = Table('Name', 'Path', 'Description', 'distance', 'UUID')
    for result in (
        db.search(query=query, table_name=_type, limit=5, max_cosine_distance=0.7)
        .to_arrow()
        .select(['uuid', 'name', 'description', '_distance'])
        .to_pylist()
    ):
        table.add_row(
            result['name'],
            '%s/%s/%s' % (config.root.root, _type, result['name']),
            result['description'],
            str(round(result['_distance'], 2)),
            result['uuid'],
        )
    console.print(table)


def list_templates(ctx: typer.Context, type: TemplateTypeEnum):
    config: StorageConfig = ctx.obj['config']
    db = VectorDatabase(uri=config.root.index_path, optimize=False)
    _type = type.value + 's'
    index = db.get_or_create_table(_type)
    table = Table('Name', 'Path', 'Description', 'UUID')
    for entry in index.to_arrow().select(['uuid', 'name', 'description']).to_pylist():
        table.add_row(
            entry['name'],
            '%s/%s/%s' % (config.root.root, _type, entry['name']),
            entry['description'],
            entry['uuid'],
        )
    console.print(table)


def copy_template(
    ctx: typer.Context,
    path: plb.Path,
    name: str | None,
    description: str | None,
    type: TemplateTypeEnum,
):
    config: StorageConfig = ctx.obj['config']
    target_storage = get_storage_backend(config.root)
    template: Template = TemplateFile.validate_python({'path': path, 'type': type.value})
    template.copy_template(
        entry=IndexEntry(name=name, description=description),
        target_storage=target_storage,
        vector_db=VectorDatabase(uri=config.root.index_path),
    )


def remove_template(ctx: typer.Context, name: str, type: TemplateTypeEnum):
    """Remove an existing template."""
    config: StorageConfig = ctx.obj['config']
    target_storage = get_storage_backend(config.root)
    vector_db = VectorDatabase(uri=config.root.index_path)

    _type = type.value + 's'

    if not vector_db.exists(_type, name):
        console.print(f'[red]{type.value.capitalize()} "{name}" does not exist.[/red]')
        raise typer.Exit(code=1)

    with Transaction(target_storage, vector_db):
        template_key = f'{_type}/{name}'
        print(f'{config.root.root}/{template_key}/**/*')
        for file in target_storage._fs.glob(f'{config.root.root}/{template_key}/**/*'):
            if target_storage._fs.isdir(file):
                continue
            _file = cast(str, file)
            target_storage.delete(_file)
        target_storage.delete(f'{config.root.root}/{template_key}', recursive=True)
        vector_db.deindex(entry=IndexEntry(name=name, type=type.value))

    console.print(f'[green]Template "{name}" has been removed.[/green]')
