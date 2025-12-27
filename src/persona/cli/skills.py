from .utils import create_cli

app = create_cli(
    name='skills',
    template_type='skills',
    help_string='Manage LLM skills.',
    description_string='skills',
)
