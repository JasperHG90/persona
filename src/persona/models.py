from pydantic import BaseModel, Field


class TemplateSummary(BaseModel):
    name: str = Field(
        ...,
        description='The name of the template (i.e. a role or skill).',
        examples=['web_scraper', 'The Master Chef'],
    )
    description: str = Field(
        ...,
        description="A brief description of the template's purpose and functionality.",
        examples=[
            'A skill that scrapes data from websites based on user-defined parameters.',
            'A role that specializes in creating gourmet recipes and cooking techniques.',
        ],
    )
    uuid: str = Field(
        ...,
        description='The unique identifier for the template. This may be a UUID, semantic version, or checksum.',
        examples=[
            '123e4567-e89b-12d3-a456-426614174000',
            'v1.0.0',
            '9c56cc51f3eb4a1d8c3e2f4b5a6d7e8f',
        ],
    )


class SkillFile(BaseModel):
    name: str = Field(
        ...,
        description='The name of the skill file.',
        examples=['web_scraper.py', 'data_analysis.ipynb', 'SKILL.md'],
    )
    content: bytes = Field(
        ...,
        description='The binary content of the skill file.',
    )
    storage_file_path: str = Field(
        ...,
        description='The relative storage path where the skill file is saved.',
        examples=['skills/web_scraper.py', 'skills/data_analysis.ipynb'],
    )
    extension: str | None = Field(
        None,
        description='The file extension of the skill file, if applicable.',
        examples=['.py', '.ipynb', '.md'],
    )


class TemplateMatch(BaseModel):
    name: str = Field(
        description='The unique identifier/name of the skill or role.',
        examples=['web_scraper', 'The Master Chef'],
    )
    description: str = Field(
        description="A brief summary of the skill or role's purpose and behavior.",
        examples=[
            'A skill that scrapes data from websites based on user-defined parameters.',
            'A role that specializes in creating gourmet recipes and cooking techniques.',
        ],
    )
    uuid: str = Field(
        description='The unique identifier (UUID, version, or checksum) of the skill or role.',
        examples=[
            '123e4567-e89b-12d3-a456-426614174000',
            'v1.0.0',
            '9c56cc51f3eb4a1d8c3e2f4b5a6d7e8f',
        ],
    )
    score: float = Field(
        description='The cosine distance; lower values indicate a closer match.',
        examples=[0.12, 0.45, 0.78],
    )
