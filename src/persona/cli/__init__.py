import uuid
import logging
import itertools
from typing import cast
from typing_extensions import Annotated
import pathlib as plb

import typer
import yaml
import frontmatter
from box import Box
from rich import print
from pydantic.v1.utils import deep_update

from .personas import app as personas_app
from .skills import app as skills_app
from .cache import app as cache_app
from .mcp import app as mcp_app
from persona.storage import IndexEntry, get_file_store_backend, get_meta_store_backend
from persona.config import parse_persona_config, PersonaConfig
from persona.embedder import get_embedding_model


logger = logging.getLogger('persona')
handler = logging.StreamHandler()
format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(format)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


app = typer.Typer(
    name='persona',
    help='Manage LLM personas and skills.',
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=True,
    pretty_exceptions_short=True,
)
app.add_typer(personas_app, name='personas', help='Manage personas.')
app.add_typer(skills_app, name='skills', help='Manage skills.')
app.add_typer(cache_app, name='cache', help='Manage the cache.')
app.add_typer(mcp_app, name='mcp', help='Manage the MCP server.')


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: Annotated[bool, typer.Option('--debug', '-d', help='Enable debug logging.')] = False,
    config: Annotated[
        plb.Path,
        typer.Option(
            '--config',
            '-c',
            help='Path to the configuration file.',
            dir_okay=False,
            exists=False,
            file_okay=True,
            readable=True,
            resolve_path=True,
            envvar='PERSONA_CONFIG_PATH',
        ),
    ] = plb.Path.home() / '.persona.config.yaml',
    set_vars: Annotated[
        list[str] | None,
        typer.Option(
            '--set',
            '-s',
            help='Override a configuration value, e.g. --set root=/path/to/root. You can use dot notation for nested values, e.g. --set file_store.type=local.',
            rich_help_panel='Configuration Overrides',
        ),
    ] = None,
):
    if debug:
        logger.setLevel(logging.DEBUG)

    box = Box(box_dots=True, default_box=True)
    if set_vars:
        for var in set_vars:
            try:
                key, value = var.split('=', 1)
                # This will automatically create nested boxes if needed
                box[key.strip()] = value.strip()
            except ValueError:
                raise typer.BadParameter(
                    f"Invalid format for --set option: '{var}'. Expected format is key=value."
                )

    overrides = box.to_dict()
    # NB: parse_persona_config reads from env vars if set
    try:
        if not config.exists():
            config_parsed = parse_persona_config(overrides)
        else:
            with config.open('r') as f:
                config_raw = yaml.safe_load(f) or {}
            config_updated = deep_update(config_raw, overrides)
            config_parsed = parse_persona_config(config_updated)
    except Exception:
        print(
            '[red][bold]Error loading configuration:[/bold][/red] malformed configuration file or invalid overrides.'
        )
        raise

    ctx.obj = {'config_path': config, 'config': config_parsed}


@app.command(help='Re-index personas and skills.')
def reindex(ctx: typer.Context):
    """Re-index personas and skills."""
    _config: PersonaConfig = ctx.obj['config']
    target_file_store = get_file_store_backend(_config.file_store)
    meta_store = get_meta_store_backend(_config.meta_store)
    embedder = get_embedding_model()
    _path = _config.root
    index = {
        'skills': [],
        'roles': [],
    }
    logger.info(f'Re-indexing templates from path: {_path}')
    for template in itertools.chain(
        target_file_store._fs.glob(f'{_path}/**/SKILL.md'),
        target_file_store._fs.glob(f'{_path}/**/PERSONA.md'),
    ):
        if target_file_store._fs.isdir(template):
            continue
        _template = cast(str, template)
        content = target_file_store.load(_template).decode('utf-8')
        fm = frontmatter.loads(content)
        entry_type = 'skill' if _template.split('/')[-1] == 'SKILL.md' else 'persona'
        fp = _template.rsplit('/', 1)[0] + '/**/*'
        description = '%s - %s' % (cast(str, fm.metadata['name']), cast(str, fm.metadata['description']))
        entry = IndexEntry(
            name=cast(str, fm.metadata['name']),
            description=description,
            uuid=uuid.uuid4().hex,  # Random init
            files=cast(list[str], target_file_store._fs.glob(fp)),  # All files in template
            embedding=embedder.encode(description).tolist()
        )
        index[entry_type + 's'].append(entry.model_dump(exclude_none=True))
    logger.info('Dropping and recreating index tables...')
    with meta_store.open():
        with meta_store.session() as session:
            session.truncate_tables()
            # NB: will be persisted to storage when _connection_ is closed
            # for duckdb, since session-based database is memory
            for k, v in index.items():
                logger.info(f'Updating table: {k} with {len(v)} entries.')
                session.upsert('roles' if k == 'roles' else 'skills', v)


@app.command(help='Initialize Persona objects on target storage.')
def init(ctx: typer.Context):
    """Initialize Persona configuration file."""
    _config: StorageConfig = ctx.obj['config']
    target_storage = get_storage_backend(_config.root)
    config_path: plb.Path = ctx.obj['config_path']
    with config_path.open('w') as f:
        yaml.safe_dump(_config.model_dump(), f)
    typer.echo(f'Initialized Persona configuration file at {config_path}')
    target_storage._fs.mkdirs(_config.root.personas_dir, exist_ok=True)
    typer.echo(f'Created personas directory at {_config.root.personas_dir}')
    target_storage._fs.mkdirs(_config.root.skills_dir, exist_ok=True)
    typer.echo(f'Created skills directory at {_config.root.skills_dir}')
    persona_index = _config.root.index_path
    typer.echo('Configuring vector database...')
    db = VectorDatabase(uri=persona_index, optimize=False)
    db.create_persona_tables()
    typer.echo(f'Created index file at {persona_index}')


def entrypoint():
    app()
