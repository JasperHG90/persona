import enum
import pathlib as plb
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from persona.config import StorageConfig
from persona.storage import get_storage_backend, IndexEntry, Index, SubIndex, Transaction
from persona.templates import TemplateFile, Template

console = Console()


class TemplateTypeEnum(str, enum.Enum):
    PERSONA = 'persona'
    SKILL = 'skill'


def list_templates(ctx: typer.Context, type: TemplateTypeEnum):
    config: StorageConfig = ctx.obj['config']
    target_storage = get_storage_backend(config.root)
    index = Index.model_validate_json(target_storage.load(target_storage.config.index))
    _type = type.value + 's'
    table = Table('Name', 'Path', 'Description', 'UUID')
    for entry_value in getattr(index, _type).root.values():
        entry_value: IndexEntry
        table.add_row(
            entry_value.name,
            '%s/%s/%s' % (config.root.root, _type, entry_value.name),
            entry_value.description,
            entry_value.uuid,
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
    )


def remove_template(ctx: typer.Context, name: str, type: TemplateTypeEnum):
    """Remove an existing template."""
    config: StorageConfig = ctx.obj['config']
    target_storage = get_storage_backend(config.root)
    index = Index.model_validate_json(target_storage.load(target_storage.config.index))

    _type = type.value + 's'

    if name not in cast(dict[str, IndexEntry], getattr(index, _type).root):
        console.print(f'[red]{type.value.capitalize()} "{name}" does not exist.[/red]')
        raise typer.Exit(code=1)

    with Transaction(target_storage):
        entry = cast(IndexEntry, getattr(index, _type).root[name])
        template_key = f'{_type}/{entry.name}'
        print(f'{config.root.root}/{template_key}/**/*')
        for file in target_storage._fs.glob(f'{config.root.root}/{template_key}/**/*'):
            if target_storage._fs.isdir(file):
                continue
            _file = cast(str, file)
            target_storage.delete(_file)
        target_storage.delete(f'{config.root.root}/{template_key}', recursive=True)
        cast(SubIndex, getattr(index, _type)).delete(cast(str, entry.name))
        target_storage.save('index.json', index.model_dump_json(indent=2))

    console.print(f'[green]Template "{name}" has been removed.[/green]')
