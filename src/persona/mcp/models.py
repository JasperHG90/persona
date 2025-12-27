from pydantic import BaseModel, PrivateAttr

from persona.config import PersonaConfig
from persona.storage import BaseFileStore, CursorLikeMetaStoreEngine
from persona.embedder import FastEmbedder


class AppContext(BaseModel):
    config: PersonaConfig
    _file_store: BaseFileStore = PrivateAttr()
    _meta_store_engine: CursorLikeMetaStoreEngine = PrivateAttr()
    _embedding_model: FastEmbedder = PrivateAttr()

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
