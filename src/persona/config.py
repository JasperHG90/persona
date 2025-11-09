import os
import pathlib as plb
from typing import Literal
from typing_extensions import Annotated
import copy

from pydantic import RootModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseStorageConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='PERSONA_STORAGE_')

    root: str = Field(default_factory=lambda: str(plb.Path.home() / '.persona'))
    index: str = 'index.json'

    @property
    def index_path(self) -> str:
        return os.path.join(self.root, self.index)


class LocalStorageConfig(BaseStorageConfig):
    type: Literal['local']


AnyStorage = Annotated[
    LocalStorageConfig,  # Can union with multiple storage configs to discriminate on type field
    Field(discriminator='type'),
]


class StorageConfig(RootModel[AnyStorage]):
    root: AnyStorage


def parse_storage_config(data: dict) -> StorageConfig:
    """Parse storage configuration from a dictionary."""
    data_ = copy.deepcopy(data)

    # Must be set otherwise discriminator won't work
    if not data_.get('type'):
        data_['type'] = os.getenv('PERSONA_STORAGE_TYPE')

    return StorageConfig.model_validate(data_)
