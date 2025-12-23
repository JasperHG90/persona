from pydantic import BaseModel, PrivateAttr

from persona.config import StorageConfig
from persona.storage import StorageBackend, VectorDatabase


class AppContext(BaseModel):
    config: StorageConfig
    _target_storage: StorageBackend = PrivateAttr()
    _vector_db: VectorDatabase = PrivateAttr()

    model_config = {'arbitrary_types_allowed': True}


class TemplateSummary(BaseModel):
    name: str
    description: str
    uuid: str


class TemplateDetails(BaseModel):
    name: str
    description: str
    prompt: str


class SkillFile(BaseModel):
    name: str
    content: bytes
    storage_file_path: str
    extension: str | None = None
