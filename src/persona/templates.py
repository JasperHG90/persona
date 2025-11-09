import logging
from abc import abstractmethod
import pathlib as plb
from typing import Literal, Self, cast
import frontmatter
from typing_extensions import Annotated
from functools import cached_property

from pydantic import Field, BaseModel, field_validator, TypeAdapter, model_validator

from persona.storage import LocalStorageBackend, StorageBackend, Transaction, Index, IndexEntry
from persona.config import LocalStorageConfig

logger = logging.getLogger('persona.core.files')


class Template(BaseModel):
    path: plb.Path

    _storage: LocalStorageBackend | None = None

    def model_post_init(self, __context) -> None:
        if self._storage is None:
            self._storage = LocalStorageBackend(
                LocalStorageConfig.model_validate(
                    {
                        'root': str(self.path) if self.path.is_dir() else str(self.path.parent),
                        'type': 'local',
                    }
                )
            )

    @abstractmethod
    def get_type(self) -> Literal['skill', 'persona']:
        raise NotImplementedError

    @property
    def is_dir(self) -> bool:
        return self.path.is_dir()

    @field_validator('path')
    def validate_path_exists(cls, v: plb.Path) -> plb.Path:
        if not v.exists():
            raise ValueError(f'Path does not exist: {v}')
        return v

    @model_validator(mode='after')
    def file_template_name_correct(self) -> Self:
        _type = 'SKILL.md' if self.get_type() == 'skill' else 'PERSONA.md'
        if self.is_dir:
            file_exists = (self.path / _type).exists()
        else:
            file_exists = self.path.name == _type
        if not file_exists:
            raise ValueError(f'Template at {self.path} is not a valid {_type} template.')
        return self

    @cached_property
    def metadata(self) -> dict[str, object] | None:
        """Load the frontmatter metadata from the template file."""
        _path = self.path.parent if not self.is_dir else self.path
        template_file = _path / ('SKILL.md' if self.get_type() == 'skill' else 'PERSONA.md')
        with template_file.open('r') as f:
            content = f.read()
        fm = frontmatter.loads(content)
        return fm.metadata

    def copy_template(self, entry: IndexEntry, target_storage: StorageBackend):
        """
        Recursively copies all files from this template's root_path to a new location.

        Args:
            target_storage: The StorageBackend instance for the destination.
            target_path: The destination directory path.
        """
        metadata = self.metadata or {}
        entry.update(
            'description', entry.description or cast(str, metadata.get('description', None))
        )
        entry.update('name', entry.name or cast(str, metadata.get('name', None)))

        if not entry.name or not entry.description:
            raise ValueError(
                'Template must have a name and description either in the frontmatter or provided during registration.'
            )

        target_key = f'{self.get_type()}s/{entry.name}'

        with Transaction(target_storage) as tx:
            local_path_root = self.path.parent if self.path.is_file() else self.path
            glob = '**/*' if plb.Path(self.path).is_dir() else self.path.name
            for filename in local_path_root.glob(glob):
                if filename.is_dir():
                    continue
                _target_key = '%s/%s' % (
                    target_key,
                    cast(str, str(filename)).removeprefix(str(local_path_root)).lstrip('/'),
                )
                logger.debug(f'Copying file {filename} to {target_key}')
                try:
                    with plb.Path(cast(str, filename)).open('r') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    logger.warning('Cannot read file %s as text, copying as binary.' % filename)
                    _fp = '%s/%s' % (target_storage.config.root, _target_key)
                    _fp_parent = str(plb.Path(_fp).parent)
                    target_storage._fs.makedirs(_fp_parent, exist_ok=True)
                    target_storage._fs.copy(str(filename), _fp)
                    continue
                if filename.name in ['PERSONA.md', 'SKILL.md']:
                    fm = frontmatter.loads(content)
                    fm.metadata.update(
                        {
                            'name': entry.name,
                            'description': entry.description,
                        }
                    )
                    content = frontmatter.dumps(fm)
                target_storage.save(_target_key, content)
            index = Index.model_validate_json(target_storage.load(target_storage.config.index))
            logger.debug(f'Transaction ID: {tx.transaction_id}')
            entry.uuid = tx.transaction_id
            index.skills.upsert(entry) if self.get_type() == 'skill' else index.personas.upsert(
                entry
            )
            target_storage.save('index.json', index.model_dump_json(indent=2))


class Skill(Template):
    type: Literal['skill'] = 'skill'

    def get_type(self) -> Literal['skill']:
        return self.type


class Persona(Template):
    type: Literal['persona'] = 'persona'

    def get_type(self) -> Literal['persona']:
        return self.type


AnyTemplate = Annotated[Skill | Persona, Field(discriminator='type')]


TemplateFile = TypeAdapter(AnyTemplate)
