import pathlib as plb
from typing_extensions import Annotated
import hashlib
import datetime as dt
import asyncio
import os
import uuid
import logging
import itertools
from typing import cast

import typer
import orjson
from rich.console import Console
import frontmatter
from fsspec.asyn import AsyncFileSystem

from persona.storage import IndexEntry
from persona.embedder import FastEmbedder
from persona.tagger import TagExtractor
from persona.cache import download_and_cache_github_repo
from persona.cli.commands import copy_template, list_templates, remove_template, match_query

console = Console()

logger = logging.getLogger('persona.cli.utils')


def create_cli(name: str, template_type: str, help_string: str, description_string: str):
    app = typer.Typer(
        name=name,
        help=help_string,
        no_args_is_help=True,
    )

    @app.command(
        'list',
        help='List all available items.',
        no_args_is_help=False,
    )
    def list_items(
        ctx: typer.Context,
    ):
        list_templates(ctx, template_type)

    @app.command(
        'register',
        help=f'Register a new {name}.',
        no_args_is_help=True,
    )
    def register_item(
        ctx: typer.Context,
        path: Annotated[
            str,
            typer.Argument(
                help=f'The path to the {name} definition file. If a github url is passed, then this is the path within the repo'
                'to the template file relative to the repo root.',
            ),
        ],
        github_url: Annotated[
            str | None,
            typer.Option(
                '--github-url',
                '-g',
                help=f'The GitHub URL of the {name} to register. Must be in format "https://github.com/<USER>/<REPO>/tree/<BRANCH>"'
                '. Path to the template must then be specified relative to the repo root.',
            ),
        ] = None,
        name: Annotated[
            str | None,
            typer.Option(
                help=f'The name of the {name} to register. If not provided, then must be described in the YAML frontmatter of the template.'
            ),
        ] = None,
        description: Annotated[
            str | None,
            typer.Option(
                help=f'A brief description of the {description_string}. If not provided, then must be described in the YAML frontmatter of the template.'
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option(
                '--tag',
                '-t',
                help=f'Tags to associate with the {name}. Can be provided multiple times. If not provided, then these will be generated automatically from the template description.',
            ),
        ] = None,
    ):
        if github_url:
            repo_path = download_and_cache_github_repo(github_url, path)
            template_path = repo_path / path
        else:
            template_path = plb.Path(path)
        copy_template(ctx, template_path, name, description, tags, template_type)

    @app.command(
        'remove',
        help=f'Remove an existing {name}.',
        no_args_is_help=True,
    )
    def remove_item(
        ctx: typer.Context,
        name: Annotated[
            str,
            typer.Argument(
                help=f'The name of the {name} to remove.',
            ),
        ],
    ):
        remove_template(ctx, name, template_type)

    @app.command(
        'match',
        help=f'Match a query to available {name}.',
        no_args_is_help=True,
    )
    def match(
        ctx: typer.Context,
        query: Annotated[
            str,
            typer.Argument(
                help=f'The description of the desired {name}.',
            ),
        ],
    ):
        match_query(ctx, query, template_type)

    return app


def _get_mtime_ts(details: dict) -> float:
    """Safely extract a unix timestamp (float) from fsspec info."""
    if not details:
        return 0.0

    val = details.get('mtime', details.get('updated'))

    if isinstance(val, dt.datetime):
        return val.timestamp()

    return float(val or 0.0)


def _get_entry_from_manifest(
    content_bytes: bytes,
    entry_type: str,
) -> IndexEntry:
    content = orjson.loads(content_bytes)
    return IndexEntry(
        name=content['name'],
        description=content['description'],
        uuid=content.get('uuid', uuid.uuid4().hex),
        etag=content.get('etag', ''),
        type=entry_type,
        files=content['files'],
        tags=content.get('tags', []),
    )


async def _get_entry_from_source(
    content_bytes: bytes,
    files: list[str],
    entry_type: str,
) -> IndexEntry:
    fm = await asyncio.to_thread(frontmatter.loads, content_bytes.decode('utf-8'))
    description = '%s - %s' % (
        cast(str, fm.metadata['name']),
        cast(str, fm.metadata['description']),
    )
    return IndexEntry(
        name=cast(str, fm.metadata['name']),
        description=description,
        uuid=uuid.uuid4().hex,  # Random init
        type=entry_type,
        etag=hashlib.md5(content_bytes).hexdigest(),
        files=files,
        tags=cast(list[str], fm.metadata.get('tags', [])),
    )


async def _template_producer(afs: AsyncFileSystem, root: str, queue: asyncio.Queue):
    """Async read templates from the storage backend and process frontmatter

    Args:
        afs (AsyncFileSystem): Async file system (ffspec)
        root (str): Root path to search for templates
        queue (asyncio.Queue): Queue to put processed templates into
    """
    patterns = [f'{root}/**/SKILL.md', f'{root}/**/ROLE.md']
    glob_results = await asyncio.gather(*(afs._glob(p) for p in patterns))
    for template in list(itertools.chain(*glob_results)):
        if await afs._isdir(template):
            continue
        _template = cast(str, template)
        entry_type = f'{_template.split("/")[-1].replace(".md", "").lower()}s'
        # Check for a manifest file and read that first
        manifest_path = f'{_template.rsplit("/", 1)[0]}/.manifest.json'
        manifest_exists = await afs._exists(manifest_path)
        entry: IndexEntry | None = None
        if manifest_exists:
            manifest_mtime = _get_mtime_ts(await afs._info(manifest_path))
            template_mtime = _get_mtime_ts(await afs._info(_template))
            if template_mtime <= manifest_mtime:
                logger.debug(f'Loading template manifest from {manifest_path}')
                content = cast(bytes, await afs._cat_file(manifest_path))
                entry = _get_entry_from_manifest(
                    content,
                    entry_type,
                )
            else:
                logger.debug(f'Manifest for {_template} is outdated!')
        if entry is None:  # Read directly from source
            logger.debug(f'Loading template source from {_template}')
            # NB: this is always text content
            content = cast(bytes, await afs._cat_file(_template))
            fp = _template.rsplit('/', 1)[0] + '/**/*'
            related_files_raw = cast(list[str], await afs._glob(fp))
            cleaned_files = [
                os.path.relpath(f, root)
                .replace('\\', '/')
                .replace('../', '')
                .replace('.persona/', '')
                for f in related_files_raw
                if not f.endswith('.manifest.json')
            ]
            entry = await _get_entry_from_source(
                content,
                cleaned_files,
                entry_type,
            )
            # Set manifest path for downstream tasks
            entry._manifest_path = manifest_path
        await queue.put(entry)
    await queue.put(None)


async def _embedding_consumer(
    afs: AsyncFileSystem,
    queue: asyncio.Queue,
    embedder: FastEmbedder,
    tagger: TagExtractor,
    index_keys: list[str],
    batch_size: int = 32,
) -> dict[str, list[dict]]:
    """Consume template frontmatter and embed them in batches of size 32

    Args:
        queue (asyncio.Queue): Queue to get processed templates from
        embedder (FastEmbedder): Embedder to encode descriptions
        batch_size (int, optional): Batch size for embedding. Defaults to 32.

    Returns:
        dict[str, list[dict]]: Dictionary with keys 'skills' and 'roles' containing lists of embedded templates.
    """
    index = {k: [] for k in index_keys}
    batch: list[IndexEntry] = []

    async def process_batch(current_batch: list[IndexEntry]):
        if not current_batch:
            return
        descriptions = [cast(str, entry.description) for entry in current_batch]
        ids = cast(list[str], [entry.name for entry in current_batch])
        embeddings = await asyncio.to_thread(embedder.encode, descriptions)
        # NB: it's simpler to just extract it for the whole batch
        tags = await asyncio.to_thread(tagger.extract_tags, ids, descriptions)
        for item, embedding in zip(current_batch, embeddings):
            item.update('embedding', embedding.tolist())
            item_name = cast(str, item.name)
            if tags.get(item_name) is not None:
                if item.tags == [] and tags[item_name] != []:
                    item.update('tags', tags[item_name])
            if item.type is None:
                raise ValueError('Item type cannot be None')
            if item.type not in index:
                raise ValueError(
                    f'Unknown item type: {item.type}, expected one of {index_keys}',
                )
            item_dict = item.model_dump(exclude_none=True, exclude={'type'})
            index[item.type].append(item_dict)
            # If manifest path is set, then we need to update it
            if item._manifest_path:
                logging.debug(f'Writing manifest at {item._manifest_path}')
                await afs._pipe(
                    item._manifest_path,
                    orjson.dumps({k: v for k, v in item_dict.items() if k != 'embedding'}),
                )

    while True:
        item = await queue.get()
        if item is None:
            # Process any remaining items in the batch
            await process_batch(batch)
            break
        batch.append(item)
        if len(batch) >= batch_size:
            await process_batch(batch)
            batch = []

        queue.task_done()
    return index
