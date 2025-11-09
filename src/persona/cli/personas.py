from .commands import TemplateTypeEnum
from .utils import create_cli

app = create_cli(
    name='persona',
    template_type=TemplateTypeEnum.PERSONA,
    help_string='Manage LLM personas.',
    description_string='persona',
)
