import typer
from rich.console import Console
from platformdirs import user_data_dir, user_cache_dir

from persona.config import PersonaConfig

console = Console()

app = typer.Typer(
    name='config',
    help='Show configuration information.',
    no_args_is_help=True,
)


@app.command('cache_dir', help='Print the location of the persona cache directory.')
def config_cache_dir():
    """Print the configuration cache directory."""
    cache_dir = user_cache_dir('persona', 'jasper_ginn', ensure_exists=False)
    console.print(str(cache_dir))


@app.command('data_dir', help='Print the location of the persona configuration data directory.')
def config_data_dir():
    """Print the configuration data directory."""
    data_dir = user_data_dir('persona', 'jasper_ginn', ensure_exists=False)
    console.print(str(data_dir))


@app.command('root_dir', help='Print the location of the persona root directory.')
def config_root_dir(ctx: typer.Context):
    """Print the persona root directory from the configuration.

    Args:
        ctx (typer.Context): Typer context
    """
    config: PersonaConfig = ctx.obj['config']
    console.print(config.root_normalized)
