import pathlib as plb
from typing_extensions import Annotated

import typer
from rich.console import Console

from persona.cache import download_and_cache_github_repo
from .commands import copy_template, list_templates, remove_template, TemplateTypeEnum

console = Console()


def create_cli(
    name: str, template_type: TemplateTypeEnum, help_string: str, description_string: str
):
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
    ):
        if github_url:
            repo_path = download_and_cache_github_repo(github_url, path)
            template_path = repo_path / path
        else:
            template_path = plb.Path(path)
        copy_template(ctx, template_path, name, description, template_type)

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

    return app
