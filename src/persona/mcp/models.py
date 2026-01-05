from typing import TYPE_CHECKING
from pydantic import BaseModel, PrivateAttr, Field

from persona.config import PersonaConfig
from persona.storage import BaseFileStore, CursorLikeMetaStoreEngine
from persona.embedder import FastEmbedder

if TYPE_CHECKING:
    from persona.api import PersonaAPI


class AppContext(BaseModel):
    config: PersonaConfig = Field(
        ...,
        description='The Persona configuration settings.',
    )
    _file_store: BaseFileStore = PrivateAttr()
    _meta_store_engine: CursorLikeMetaStoreEngine = PrivateAttr()
    _embedding_model: FastEmbedder = PrivateAttr()
    _api: 'PersonaAPI' = PrivateAttr()

    model_config = {'arbitrary_types_allowed': True}


class TemplateDetails(BaseModel):
    name: str = Field(
        ..., description='The name of the role.', examples=['The Master Chef', 'python_engineer']
    )
    description: str = Field(
        ...,
        description="A brief description of the role's purpose and functionality.",
        examples=[
            'A role that specializes in creating gourmet recipes and cooking techniques.',
            'A role that writes and debugs Python code for various applications.',
        ],
    )
    prompt: str = Field(
        ...,
        description='The prompt text associated with the role.',
        examples=[
            'You are The Master Chef, an expert in culinary arts. Provide detailed recipes and cooking tips.',
            'You are a Python engineer skilled in writing efficient and clean code. Assist with coding tasks.',
        ],
    )
