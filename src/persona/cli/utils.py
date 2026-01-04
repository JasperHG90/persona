import pathlib as plb
from typing_extensions import Annotated

import typer
import orjson
from rich.console import Console
import asyncio
import os
import uuid
import itertools
from typing import cast

import frontmatter
from fsspec.asyn import AsyncFileSystem

from persona.storage import IndexEntry
from persona.embedder import FastEmbedder
from persona.tagger import TagExtractor
from persona.cache import download_and_cache_github_repo
from persona.cli.commands import copy_template, list_templates, remove_template, match_query

console = Console()


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
        manifest_path = os.path.join(_template.rsplit('/', 1)[0], '.manifest.json')
        if await afs._exists(manifest_path):
            content = orjson.loads(cast(bytes, await afs._cat_file(manifest_path)))
            entry = IndexEntry(
                name=content['name'],
                description=content['description'],
                uuid=content.get('uuid', uuid.uuid4().hex),
                type=entry_type,
                files=content['files'],
                tags=content.get('tags', None),
            )
        else:
            # NB: this is always text content
            content = cast(bytes, await afs._cat_file(_template)).decode('utf-8')
            fm = await asyncio.to_thread(frontmatter.loads, content)
            fp = _template.rsplit('/', 1)[0] + '/**/*'
            description = '%s - %s' % (
                cast(str, fm.metadata['name']),
                cast(str, fm.metadata['description']),
            )
            related_files_raw = cast(list[str], await afs._glob(fp))
            cleaned_files = [
                os.path.relpath(f, root).replace('../', '').replace('.persona/', '')
                for f in related_files_raw
            ]
            entry = IndexEntry(
                name=cast(str, fm.metadata['name']),
                description=description,
                uuid=uuid.uuid4().hex,  # Random init
                type=entry_type,
                files=cleaned_files,
                tags=cast(list[str] | None, fm.metadata.get('tags', None)),
            )
            # Save manifest
            # NB: This speeds up future reads, but requires **write** permissions
            # to the storage backend
            await afs._pipe(
                manifest_path, orjson.dumps(entry.model_dump(exclude_none=True, exclude={'type'}))
            )
        await queue.put(entry)
    await queue.put(None)


async def _embedding_consumer(
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
            if item.tags is None:
                item.update('tags', tags.get(cast(str, item.name), []))
            if item.type is None:
                raise ValueError('Item type cannot be None')
            if item.type not in index:
                raise ValueError(
                    f'Unknown item type: {item.type}, expected one of {index_keys}',
                )
            index[item.type].append(item.model_dump(exclude_none=True, exclude={'type'}))

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
