import asyncio
import logging
from typing import cast
from typing_extensions import Annotated
import pathlib as plb

import typer
import yaml
from box import Box
from rich import print
from pydantic.v1.utils import deep_update
from fsspec.implementations.asyn_wrapper import AsyncFileSystemWrapper
from fsspec.implementations.local import LocalFileSystem
from fsspec.asyn import AsyncFileSystem

from .roles import app as roles_app
from .skills import app as skills_app
from .cache import app as cache_app
from .mcp import app as mcp_app
from .config import app as config_app
from .utils import _template_producer, _embedding_consumer
from persona.storage import get_file_store_backend, get_meta_store_backend
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
    help='Manage LLM roles and skills.',
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=True,
    pretty_exceptions_short=True,
)
app.add_typer(roles_app, name='roles', help='Manage roles.')
app.add_typer(skills_app, name='skills', help='Manage skills.')
app.add_typer(cache_app, name='cache', help='Manage the cache.')
app.add_typer(mcp_app, name='mcp', help='Manage the MCP server.')
app.add_typer(config_app, name='config', help='Show configuration information.')


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
    config_raw: dict = {}
    try:
        if not config.exists():
            config_parsed = parse_persona_config(overrides)
        else:
            with config.open('r') as f:
                config_raw = cast(dict, yaml.safe_load(f) or {})
                # NB: validate the raw config if it exists
                # This also adds default values for optional fields
                config_validated = PersonaConfig.model_validate(config_raw).model_dump()
            config_updated = deep_update(config_validated, overrides)
            config_parsed = parse_persona_config(config_updated)
    except Exception:
        print(
            '[red][bold]Error loading configuration:[/bold][/red] malformed configuration file or invalid overrides.'
        )
        raise

    ctx.obj = {
        'config_path': config,
        'config': config_parsed,
        'config_on_disk': config_raw,
        'config_overrides': overrides,
    }


@app.command(help='Re-index personas and skills.')
def reindex(ctx: typer.Context):
    """Re-index personas and skills."""
    _config: PersonaConfig = ctx.obj['config']
    target_file_store = get_file_store_backend(_config.file_store)
    meta_store = get_meta_store_backend(_config.meta_store, read_only=False)
    embedder = get_embedding_model()
    _path = _config.root

    async def run_pipeline():
        # NB: reindexing would gain from async ffspec interface, so we re-init it
        #  here from the file store backend config instead of implementing an async version
        #  this batches template frontmatter in an async queue so we can get embeddings in a
        #  somewhat efficient manner.
        # NB: Local file system has no async implementation, so we use the async file system wrapper
        afs = cast(
            AsyncFileSystem,
            type(target_file_store._fs)(**target_file_store._fs.storage_options, asynchronous=True),
        )
        if isinstance(target_file_store._fs, LocalFileSystem):
            afs = AsyncFileSystemWrapper(afs)
        queue = asyncio.Queue(maxsize=128)
        producer_task = asyncio.create_task(_template_producer(afs, _path, queue))
        consumer_task = asyncio.create_task(_embedding_consumer(queue, embedder, batch_size=32))
        await asyncio.gather(producer_task)
        results = await consumer_task
        return results

    index = asyncio.run(run_pipeline())

    logger.info('Dropping and recreating index tables...')
    with meta_store.open(bootstrap=True) as connected:
        with connected.session() as session:
            session.truncate_tables()
            # NB: will be persisted to storage when **connection** is closed
            # for duckdb, since session-based database is memory
            for k, v in index.items():
                logger.info(f'Updating table: {k} with {len(v)} entries.')
                # NB: type hint is literal so using k makes pylance unhappy
                session.upsert('roles' if k == 'roles' else 'skills', v)


@app.command(help='Initialize Persona objects on target storage.')
def init(ctx: typer.Context):
    """Initialize Persona configuration file."""
    _config: PersonaConfig = ctx.obj['config']
    target_storage = get_file_store_backend(_config.file_store)
    meta_store = get_meta_store_backend(_config.meta_store, read_only=False)
    config_path: plb.Path = ctx.obj['config_path']
    # NB: this writes any overrides back to the config file
    # When doing an init, we don't want to get the validated values with defaults filled in
    config_ = deep_update(ctx.obj['config_on_disk'], ctx.obj['config_overrides'])
    with config_path.open('w') as f:
        yaml.safe_dump(parse_persona_config(config_).model_dump(), f)
    # NB: this needs to be refactored if the metadata store backend is not file-based
    typer.echo(f'Initialized Persona configuration file at {config_path}')
    target_storage._fs.mkdirs(_config.file_store.roles_dir, exist_ok=True)
    typer.echo(f'Created roles directory at {_config.file_store.roles_dir}')
    target_storage._fs.mkdirs(_config.file_store.skills_dir, exist_ok=True)
    typer.echo(f'Created skills directory at {_config.file_store.skills_dir}')
    persona_index = _config.meta_store.index_path
    # NB: if a metastore backend has a root, then the index path needs to be created on
    #  the target storage file system.
    if hasattr(_config.meta_store, 'root'):
        target_storage._fs.mkdirs(persona_index, exist_ok=True)
    typer.echo('Configuring vector database...')
    with meta_store.open() as connected:
        connected.bootstrap()
    typer.echo(f'Created index file at {persona_index}')
    typer.echo('Downloading embedding model...')
    _ = get_embedding_model()


def entrypoint():
    app()
