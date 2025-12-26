import os
import pathlib as plb
from typing import Literal, Union
from typing_extensions import Annotated
import copy

from pydantic import Field, model_validator, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigWithRoot(BaseModel):
    """Settings shared by a root folder."""
    root: str | None = None


class BaseFileStoreConfig(ConfigWithRoot):
    @property
    def roles_dir(self) -> str:
        if not self.root:
            raise ValueError("Root path is not set.")
        return os.path.join(self.root, 'roles')

    @property
    def skills_dir(self) -> str:
        if not self.root:
            raise ValueError("Root path is not set.")
        return os.path.join(self.root, 'skills')


class LocalFileStoreConfig(BaseFileStoreConfig):
    type: Literal['local'] = 'local'


FileStoreBackend = Annotated[
    Union[LocalFileStoreConfig],
    Field(discriminator='type')
]


class SimilaritySearchConfig(BaseModel):
    model: Literal["sentence-transformers/all-MiniLM-L6-v2"] = "sentence-transformers/all-MiniLM-L6-v2"
    max_cosine_distance: float = 0.5
    max_results: int = 5


class BaseMetaStoreConfig(BaseModel):
    similarity_search: SimilaritySearchConfig = Field(default_factory=lambda: SimilaritySearchConfig())


class DuckDBMetaStoreConfig(BaseMetaStoreConfig, ConfigWithRoot):
    type: Literal['duckdb'] = 'duckdb'
    root: str | None = None
    index_folder: str = 'index'
    
    @property
    def index_path(self) -> str:
        if not self.root:
            raise ValueError("Root path is not set.")
        return os.path.join(self.root, self.index_folder)
    
    @property
    def roles_index_path(self) -> str:
        if not self.root:
            raise ValueError("Root path is not set.")
        return os.path.join(self.index_path, 'roles.parquet')

    @property
    def skills_index_path(self) -> str:
        if not self.root:
            raise ValueError("Root path is not set.")
        return os.path.join(self.index_path, 'skills.parquet')


MetaStoreBackend = Annotated[
    Union[DuckDBMetaStoreConfig],
    Field(discriminator='type')
]


class PersonaConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='PERSONA_', 
        env_nested_delimiter='__'
    )
    
    root: str = Field(default_factory=lambda: str(plb.Path.home() / '.persona'))
    
    file_store: FileStoreBackend = Field(default_factory=lambda: LocalFileStoreConfig())
    meta_store: MetaStoreBackend = Field(default_factory=lambda: DuckDBMetaStoreConfig())

    @model_validator(mode='after')
    def sync_root_paths(self) -> 'PersonaConfig':
        """
        Automatically propagate the top-level root to sub-configs 
        if they haven't been overridden.
        """
        if self.file_store.root is None:
            self.file_store.root = self.root
        # NB: if this is an attribute and None, then propage the root value
        if hasattr(self.meta_store, 'root'):            
            if self.meta_store.root is None:
                self.meta_store.root = self.root
        return self


def parse_persona_storage_config(data: dict) -> PersonaConfig:
    """Parse persona config from a dictionary."""
    data_ = copy.deepcopy(data)

    if data['file_store'].get('type') is None:
        data_['file_store']['type'] = 'local'
    if data['meta_store'].get('type') is None:
        data_['meta_store']['type'] = 'duckdb'

    return PersonaConfig.model_validate(data_, extra="forbid")

