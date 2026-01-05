import pathlib as plb
import os
from typing import cast
import frontmatter

from persona.config import PersonaConfig
from persona.storage import BaseFileStore, CursorLikeMetaStoreEngine, IndexEntry, Transaction
from persona.embedder import FastEmbedder
from persona.tagger import get_tagger
from persona.templates import TemplateFile, Template
from persona.models import SkillFile
from persona.types import personaTypes

# Moved back to mcp/utils/const.py or passed in as config if needed globally
# For now, we will allow injecting a whitelist or default to a safe list if strictly necessary here,
# but the instruction was to keep MCP specific stuff in MCP.
# However, "install_skill" needs to know what files to write.
# We will accept an optional whitelist in methods or use a sensible default.
DEFAULT_EXT_WHITELIST = [
    '.md',
    '.txt',
    '.json',
    '.yaml',
    '.yml',
    '.cfg',
    '.ini',
    '.py',
    '.js',
    '.ts',
    '.html',
    '.css',
]


class PersonaAPI:
    def __init__(
        self,
        config: PersonaConfig,
        meta_store: CursorLikeMetaStoreEngine,
        file_store: BaseFileStore | None = None,
        embedder: FastEmbedder | None = None,
        library_skills: dict[str, dict[str, SkillFile]] | None = None,
    ):
        """Convenient access to the Persona API

        Args:
            config (PersonaConfig): Persona configuration
            file_store (BaseFileStore): A file store backend.
            meta_store (CursorLikeMetaStoreEngine): A meta store backend. NB: If provided, then it **must** already be bootstrapped.
            embedder (FastEmbedder): An embedder instance.
            library_skills (dict[str, dict[str, SkillFile]] | None, optional): A dictionary of library skills. Defaults to None.
        """
        if not meta_store._bootstrapped:
            raise ValueError('Provided meta_store must already be bootstrapped.')

        self.config = config
        self._file_store = file_store
        self._meta_store = meta_store
        self._embedder = embedder
        self._library_skills = library_skills or {}

    def _requires_embedder(self):
        if not self._embedder:
            raise ValueError('Embedder instance is required for this operation.')

    def _requires_file_store(self):
        if not self._file_store:
            raise ValueError('File store instance is required for this operation.')

    def list_templates(self, type: personaTypes, columns: list[str]) -> list[dict]:
        """List templates of a specific type."""
        with self._meta_store.read_session() as session:
            results = session.get_many(
                table_name=type,
                column_filter=columns,
            ).to_pylist()
        return results

    def search_templates(
        self,
        query: str,
        type: personaTypes,
        columns: list[str],
        limit: int | None = None,
        max_cosine_distance: float | None = None,
    ) -> list[dict]:
        """Search templates by query."""
        self._requires_embedder()
        limit = limit or self.config.meta_store.similarity_search.max_results
        max_cosine_distance = (
            max_cosine_distance or self.config.meta_store.similarity_search.max_cosine_distance
        )

        query_vector = cast(FastEmbedder, self._embedder).encode([query]).squeeze().tolist()

        with self._meta_store.read_session() as session:
            results = session.search(
                query=query_vector,
                table_name=type,
                limit=limit,
                column_filter=columns,
                max_cosine_distance=max_cosine_distance,
            ).to_pylist()

        return results

    def get_role(self, name: str) -> bytes:
        """Get role raw content."""
        self._requires_file_store()

        with self._meta_store.read_session() as session:
            if not session.exists('roles', name):
                raise ValueError(f"Role '{name}' does not exist.")

        role_path = f'roles/{name}/ROLE.md'
        return cast(BaseFileStore, self._file_store).load(role_path)

    def get_skill_files(self, name: str) -> dict[str, bytes]:
        """Get all raw files for a skill."""
        self._requires_file_store()
        # Library skills are already raw bytes in self._library_skills if we store them that way
        # or we need to adapt _get_builtin_skills
        if name in self._library_skills:
            return {fn: obj.content for fn, obj in self._library_skills[name].items()}

        with self._meta_store.read_session() as session:
            if not session.exists('skills', name):
                raise ValueError(f"Skill '{name}' does not exist.")

            skill_data = session.get_one('skills', name, ['files']).to_pylist()[0]

        skill_files_paths = skill_data['files']

        results = {}
        for storage_path in skill_files_paths:
            filename = storage_path.rsplit('/', 1)[-1]
            results[filename] = cast(BaseFileStore, self._file_store).load(storage_path)

        return results

    def _skill_files(self, name: str) -> dict[str, SkillFile]:
        """Get a skill by name (logic)."""
        with self._meta_store.read_session() as session:
            if session.exists('skills', name):
                skill_files = cast(
                    dict[str, str],
                    session.get_one('skills', name, ['name', 'files', 'uuid']).to_pylist()[0],
                )

                # Load SKILL.md and inject version
                # Note: This assumes SKILL.md is always present and in the list, which it should be.
                skill_md_path = f'skills/{name}/SKILL.md'
                raw_content = (
                    cast(BaseFileStore, self._file_store).load(skill_md_path).decode('utf-8')
                )
                content = frontmatter.loads(raw_content)

                # content.metadata might be None if empty
                if content.metadata is None:
                    content.metadata = {}

                content.metadata['metadata'] = {'version': skill_files['uuid']}

                results = {
                    'SKILL.md': SkillFile(
                        content=frontmatter.dumps(content).encode('utf-8'),
                        name='SKILL.md',
                        storage_file_path=skill_md_path,
                        extension='.md',
                    )
                }

                for target_store_file in skill_files['files']:
                    # Logic from snippet:
                    file = target_store_file.rsplit('/', 1)[-1]
                    ext = os.path.splitext(file)[-1]

                    # Use the whitelist defined in api.py or the imported constant
                    # The snippet used EXT_WHITELIST. api.py has DEFAULT_EXT_WHITELIST.
                    if ext not in DEFAULT_EXT_WHITELIST:
                        continue
                    elif file.endswith('SKILL.md'):
                        continue
                    else:
                        _file_content = cast(BaseFileStore, self._file_store).load(
                            target_store_file
                        )
                        results[file] = SkillFile(
                            content=_file_content,
                            name=file,
                            storage_file_path=target_store_file,
                            extension=ext,
                        )
                return results
            else:
                raise ValueError(f'Skill "{name}" not found')

    def install_skill(self, name: str, local_skill_dir: plb.Path) -> str:
        """Install a skill to a local directory."""
        self._requires_file_store()
        if not local_skill_dir.is_absolute():
            raise ValueError(f"Path '{local_skill_dir}' must be absolute.")
        if not local_skill_dir.exists():
            raise ValueError(f"Path '{local_skill_dir}' does not exist.")

        # Check library skills first
        skill_files = self._library_skills.get(name)
        if not skill_files:
            skill_files = self._skill_files(name)

        skill_md_local_path: str | None = None

        for filename, file_obj in skill_files.items():
            # Standardize destination path
            # If storage_file_path is relative to the skills root (e.g. skills/name/...), we want to preserve that structure under local_skill_dir
            # The snippet logic: dest = dir_ / file.storage_file_path.replace('skills/', '')

            # For library skills, we might need to handle storage_file_path differently if it doesn't start with skills/
            # But let's assume storage_file_path is always set correctly or we use a fallback.

            rel_path = file_obj.storage_file_path.replace('skills/', '')
            # Remove leading slash if present after replace (though usually it won't be if it was 'skills/...')
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]

            dest = local_skill_dir / rel_path

            if not dest.parent.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)

            with dest.open('wb') as f:
                f.write(file_obj.content)

            if filename == 'SKILL.md':
                skill_md_local_path = str(dest)

        if not skill_md_local_path:
            raise ValueError(f"SKILL.md not found for skill '{name}'.")

        return skill_md_local_path

    def publish_template(
        self,
        path: plb.Path,
        type: personaTypes,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ):
        """Publish a template to the store."""
        self._requires_file_store()
        self._requires_embedder()
        tagger = get_tagger(cast(FastEmbedder, self._embedder))
        template: Template = TemplateFile.validate_python({'path': path, 'type': type})

        # Transaction handling needs to be careful with injected engines
        # Transaction class usually expects to manage the commit/rollback logic

        with Transaction(cast(BaseFileStore, self._file_store), self._meta_store):
            template.process_template(
                entry=IndexEntry(name=name, description=description, tags=tags or []),
                target_file_store=cast(BaseFileStore, self._file_store),
                meta_store_engine=self._meta_store,
                embedder=cast(FastEmbedder, self._embedder),
                tagger=tagger,
            )

    def delete_template(self, name: str, type: personaTypes):
        """Delete a template."""
        self._requires_file_store()
        fs = cast(BaseFileStore, self._file_store)
        with Transaction(fs, self._meta_store):
            with self._meta_store.read_session() as session:  # Check existence
                if not session.exists(type, name):
                    raise ValueError(f"{type.capitalize()} '{name}' does not exist.")

            template_key = f'{type}/{name}'
            for file in fs.glob(f'{template_key}/**/*'):
                if fs.is_dir(file):
                    continue
                fs.delete(cast(str, file))
            fs.delete(template_key, recursive=True)
            self._meta_store.deindex(entry=IndexEntry(name=name, type=type))

    def get_skill_version(self, name: str) -> str:
        """Get the version (UUID) of a skill."""
        with self._meta_store.open(bootstrap=False):
            with self._meta_store.read_session() as session:
                if not session.exists('skills', name):
                    raise ValueError(f"Skill '{name}' not found.")
                result = session.get_one('skills', name, ['uuid']).to_pylist()[0]
                return result['uuid']
