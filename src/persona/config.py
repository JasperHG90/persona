import os
import pathlib as plb
from typing import Literal, Union
from typing_extensions import Annotated
import copy
from platformdirs import user_data_dir

from pydantic import Field, model_validator, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigWithRoot(BaseModel):
    """Settings shared by a root folder."""

    root: str | None = Field(
        default=None,
        description='The root directory for storing data. If not set, '
        'will default to the top-level PersonaConfig root path.',
    )


class BaseFileStoreConfig(ConfigWithRoot):
    @property
    def roles_dir(self) -> str:
        if not self.root:
            raise ValueError('Root path is not set.')
        return os.path.join(self.root, 'roles')

    @property
    def skills_dir(self) -> str:
        if not self.root:
            raise ValueError('Root path is not set.')
        return os.path.join(self.root, 'skills')


class LocalFileStoreConfig(BaseFileStoreConfig):
    type: Literal['local'] = 'local'


FileStoreBackend = Annotated[Union[LocalFileStoreConfig], Field(discriminator='type')]


class SimilaritySearchConfig(BaseModel):
    model: Literal['sentence-transformers/all-MiniLM-L6-v2-quantized'] = (
        'sentence-transformers/all-MiniLM-L6-v2-quantized'
    )
    max_cosine_distance: float = Field(
        default=0.8,
        description='Maximum cosine distance threshold for similarity search.',
    )
    max_results: int = Field(
        default=3,
        description='Maximum number of results to return from similarity search.',
    )


class BaseMetaStoreConfig(BaseModel):
    similarity_search: SimilaritySearchConfig = Field(
        default_factory=lambda: SimilaritySearchConfig(),
        description='Configuration for similarity search in the meta store.',
    )


class FileStoreBasedMetaStoreConfig(BaseMetaStoreConfig, ConfigWithRoot):
    root: str | None = Field(
        default=None,
        description='The root directory for storing DuckDB index files. If not set, '
        'will default to the top-level PersonaConfig root path.',
    )
    index_folder: str = Field(
        default='index',
        description='Folder within the root directory to store index files. The DuckDB metastore '
        'implementation will store the index files as parquet files on the same storage backend as '
        ' the file store. Defaults to "index".',
    )

    @property
    def index_path(self) -> str:
        """Directory on the file store backend where index files are stored."""
        if not self.root:
            raise ValueError('Root path is not set.')
        return os.path.join(self.root, self.index_folder)

    @property
    def roles_index_path(self) -> str:
        """Path to the roles index parquet file."""
        if not self.root:
            raise ValueError('Root path is not set.')
        return os.path.join(self.index_path, 'roles.parquet')

    @property
    def skills_index_path(self) -> str:
        """Path to the skills index parquet file."""
        if not self.root:
            raise ValueError('Root path is not set.')
        return os.path.join(self.index_path, 'skills.parquet')


class DuckDBMetaStoreConfig(FileStoreBasedMetaStoreConfig, ConfigWithRoot):
    type: Literal['duckdb'] = 'duckdb'


MetaStoreBackend = Annotated[Union[DuckDBMetaStoreConfig], Field(discriminator='type')]


class PersonaConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='PERSONA_', env_nested_delimiter='__', extra='forbid'
    )

    root: str = Field(
        default_factory=lambda: user_data_dir('persona', 'jasper_ginn'),
        description='The root directory for Persona file store and for some meta store backends. '
        'Defaults to the user data directory.',
        examples=['/home/vscode/.local/share/persona', 'gs://my-bucket/persona'],
    )

    file_store: FileStoreBackend = Field(
        default_factory=lambda: LocalFileStoreConfig(),
        description='Configuration for the file storage backend. Defaults to local file storage.',
    )
    meta_store: MetaStoreBackend = Field(
        default_factory=lambda: DuckDBMetaStoreConfig(),
        description='Configuration for the metadata storage backend. Defaults to a DuckDB metadata '
        'store that stores indexes as parquet files in the user data directory.',
    )

    @property
    def root_normalized(self) -> str:
        """Get the normalized root path."""
        return str(plb.Path(self.root).expanduser().resolve())

    @model_validator(mode='after')
    def sync_root_paths(self) -> 'PersonaConfig':
        """
        Automatically propagate the top-level root to sub-configs
        if they haven't been overridden.
        """
        if self.file_store.root is None:
            self.file_store.root = self.root
        # NB: if this is an attribute and None, then propage the root value
        #  this only happens for file-store-based meta stores
        if hasattr(self.meta_store, 'root'):
            if self.meta_store.root is None:
                self.meta_store.root = self.root
        return self


def parse_persona_config(data: dict) -> PersonaConfig:
    """Parse persona config from a dictionary."""
    data_ = copy.deepcopy(data)

    if data['file_store'].get('type') is None:
        data_['file_store']['type'] = 'local'
    if data['meta_store'].get('type') is None:
        data_['meta_store']['type'] = 'duckdb'

    return PersonaConfig(**data_)
