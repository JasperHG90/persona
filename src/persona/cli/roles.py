from persona.cli.utils import create_cli

app = create_cli(
    name='roles',
    template_type='roles',
    help_string='Manage LLM roles.',
    description_string='roles',
)
