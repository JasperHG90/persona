import datetime as dt

from pydantic import BaseModel, Field, field_serializer


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
    tags: list[str] = Field(
        default_factory=list,
        description='List of tags associated with the template',
        examples=[['assistant', 'helpful', 'task-management']],
    )
    type: str | None = Field(
        default=None, description='The type of the template', examples=['roles', 'skills']
    )
    date_created: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc),
        description='The timestamp when the template was created',
    )

    @field_serializer('date_created')
    def serialize_date_created(self, date_created: dt.datetime) -> str:
        return date_created.isoformat()

    def update(self, key: str, value: list[float] | list[str] | str | None):
        setattr(self, key, value)
