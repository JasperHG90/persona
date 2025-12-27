import logging
from abc import abstractmethod
import pathlib as plb
from typing import Literal, Self, cast
import frontmatter
from typing_extensions import Annotated
from functools import cached_property

from pydantic import Field, BaseModel, field_validator, TypeAdapter, model_validator

from persona.storage import (
    IndexEntry,
    BaseFileStore,
    CursorLikeMetaStoreEngine,
    LocalFileStore,
)
from persona.config import LocalFileStoreConfig
from persona.embedder import FastEmbedder

logger = logging.getLogger('persona.core.files')


def _is_persona_root_file(path: plb.Path) -> bool:
    return path.name in ['ROLE.md', 'SKILL.md']


class SourceFile:
    def __init__(
        self,
        path: plb.Path,
        source_path_root: plb.Path | None = None,
        target_path_root: str | None = None,
    ) -> None:
        self.path = path
        self.source_path_root = source_path_root
        self.target_path_root = target_path_root

    @cached_property
    def content(self) -> bytes:
        return self.path.read_bytes()

    @property
    def target_key(self) -> str:
        return '%s/%s' % (
            self.target_path_root,
            cast(str, str(self.path)).removeprefix(str(self.source_path_root)).lstrip('/'),
        )


class PersonaRootSourceFile(SourceFile):
    @cached_property
    def frontmatter(self) -> frontmatter.Post:
        return frontmatter.loads(self.content.decode('utf-8'))

    @cached_property
    def metadata(self) -> dict[str, object] | None:
        return self.frontmatter.metadata

    def update_metadata(self, name: str | None, description: str | None) -> bytes:
        fm = self.frontmatter
        fm.metadata.update(
            {
                'name': name,
                'description': description,
            }
        )
        return frontmatter.dumps(fm).encode('utf-8')


class Template(BaseModel):
    path: plb.Path

    _file_store: BaseFileStore | None = None

    def model_post_init(self, __context) -> None:
        if self._storage is None:
            # NB: use local file store to read templates as they should always be on-disk locally.
            self._storage = LocalFileStore(
                LocalFileStoreConfig.model_validate(
                    {
                        'root': str(self.path) if self.path.is_dir() else str(self.path.parent),
                        'type': 'local',
                    }
                )
            )

    @abstractmethod
    def get_type(self) -> Literal['skill'] | Literal['role']:
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
        _type = 'SKILL.md' if self.get_type() == 'skill' else 'ROLE.md'
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
        template_file = _path / ('SKILL.md' if self.get_type() == 'skill' else 'ROLE.md')
        with template_file.open('r') as f:
            content = f.read()
        fm = frontmatter.loads(content)
        return fm.metadata

    def process_template(
        self,
        entry: IndexEntry,
        target_file_store: BaseFileStore,
        meta_store_engine: CursorLikeMetaStoreEngine,
        embedder: FastEmbedder,
    ) -> None:
        """Recursively copies all files in the directory of a template to the target file store.

        Args:
            entry (IndexEntry): Metadata entry that will be written to the metadata store.
            target_file_store (BaseFileStore): File store to which template will be copied.
            meta_store_engine (CursorLikeMetaStoreEngine): Metastore engine. Used to track metadata.
            embedder (FastEmbedder): Embedding model used to embed the template description.

        Raises:
            ValueError: raised if either the entry name or description is not set.
        """
        metadata = self.metadata or {}
        entry.update(
            'description', entry.description or cast(str, metadata.get('description', None))
        )
        entry.update('name', entry.name or cast(str, metadata.get('name', None)))
        entry.update('type', self.get_type())

        if entry.name is None or entry.description is None:
            raise ValueError(
                'Template must have a name and description either in the frontmatter or provided during registration.'
            )

        entry.update('embedding', embedder.encode(entry.description).tolist())

        target_key = f'{self.get_type()}s/{entry.name}'

        local_path_root = self.path.parent if self.path.is_file() else self.path
        glob = '**/*' if plb.Path(self.path).is_dir() else self.path.name

        files: list[str] = []
        for filename in local_path_root.glob(glob):
            if filename.is_dir():
                continue
            kwargs = {
                'path': filename,
                'source_path_root': local_path_root,
                'target_path_root': target_key,
            }
            file_ = (
                SourceFile(**kwargs)
                if not _is_persona_root_file(filename)
                else PersonaRootSourceFile(**kwargs)
            )

            if isinstance(file_, PersonaRootSourceFile):
                content = file_.update_metadata(entry.name, entry.description)
            else:
                content = file_.content

            target_file_store.save(file_.target_key, content)

            files.append(file_.target_key)

        entry.update('files', files)
        meta_store_engine.index(entry)


class Skill(Template):
    type: Literal['skill'] = 'skill'

    def get_type(self) -> Literal['skill']:
        return self.type


class Role(Template):
    type: Literal['role'] = 'role'

    def get_type(self) -> Literal['role']:
        return self.type


AnyTemplate = Annotated[Skill | Role, Field(discriminator='type')]


TemplateFile = TypeAdapter(AnyTemplate)
