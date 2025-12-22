from pydantic import BaseModel, PrivateAttr

from persona.config import StorageConfig
from persona.storage import StorageBackend


class AppContext(BaseModel):
    config: StorageConfig
    _target_storage: StorageBackend = PrivateAttr()

    model_config = {'arbitrary_types_allowed': True}


class TemplateSummary(BaseModel):
    name: str
    description: str
    uuid: str


class TemplateDetails(BaseModel):
    name: str
    description: str
    prompt: str
