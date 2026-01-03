from pydantic import BaseModel, Field


class IndexEntry(BaseModel):
    name: str | None = Field(
        default=None, description='The name of the template', examples=['helpful-assistant']
    )
    description: str | None = Field(
        default=None,
        description='A brief description of the template',
        examples=['A helpful role that assists users in managing tasks.'],
    )
    uuid: str | None = Field(
        default=None,
        description='The unique identifier of the template',
        examples=['123e4567-e89b-12d3-a456-426614174000'],
    )
    files: list[str] | None = Field(
        default=None,
        description='List of files associated with the template',
        examples=[
            ['ROLE.md'],
            ['skills/helpful-assistant/SKILL.md', 'skills/helpful-assistant/scripts/utils.py'],
        ],
    )
    embedding: list[float] | None = Field(
        default=None,
        description='The embedding vector representing the template for similarity searches',
    )
    type: str | None = Field(
        default=None, description='The type of the template', examples=['roles', 'skills']
    )

    def update(self, key: str, value: list[float] | list[str] | str | None):
        setattr(self, key, value)
