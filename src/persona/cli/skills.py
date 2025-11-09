from .commands import TemplateTypeEnum
from .utils import create_cli

app = create_cli(
    name='skill',
    template_type=TemplateTypeEnum.SKILL,
    help_string='Manage LLM skills.',
    description_string='skill',
)
