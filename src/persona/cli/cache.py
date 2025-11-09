import shutil

import typer
from rich.console import Console

from persona.cache import PERSONA_CACHE

console = Console()

app = typer.Typer(
    name='cache',
    help='Manage the cache.',
    no_args_is_help=True,
)


@app.command('clean')
def clean_cache():
    """Clean the cache."""
    if len([*PERSONA_CACHE.glob('*')]) > 0:
        shutil.rmtree(PERSONA_CACHE)
        console.print(f'Cache cleaned at {PERSONA_CACHE}')
    else:
        console.print('Cache is empty.')
    PERSONA_CACHE.mkdir(parents=True, exist_ok=True)


@app.command('dir')
def cache_dir():
    """Print the cache directory."""
    console.print(str(PERSONA_CACHE))
