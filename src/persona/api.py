import pathlib as plb
from typing import cast

from persona.config import PersonaConfig
from persona.storage import (
    BaseFileStore,
    CursorLikeMetaStoreEngine,
    IndexEntry,
    Transaction,
    get_file_store_backend,
    get_meta_store_backend,
)
from persona.embedder import get_embedding_model, FastEmbedder
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
        file_store: BaseFileStore | None = None,
        meta_store: CursorLikeMetaStoreEngine | None = None,
        embedder: FastEmbedder | None = None,
        library_skills: dict[str, dict[str, SkillFile]] | None = None,
    ):
        self.config = config
        self._file_store = file_store
        self._meta_store = meta_store
        self._embedder = embedder
        self._library_skills = library_skills or {}

    @property
    def file_store(self) -> BaseFileStore:
        if self._file_store is None:
            self._file_store = get_file_store_backend(self.config.file_store)
        return self._file_store

    @property
    def meta_store(self) -> CursorLikeMetaStoreEngine:
        if self._meta_store is None:
            # If not provided, we create a new connection (e.g. CLI usage)
            self._meta_store = get_meta_store_backend(self.config.meta_store)
        return self._meta_store

    @property
    def embedder(self) -> FastEmbedder:
        if self._embedder is None:
            self._embedder = get_embedding_model()
        return self._embedder

    def list_templates(self, type: personaTypes, columns: list[str]) -> list[dict]:
        """List templates of a specific type."""
        with self.meta_store.read_session() as session:
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
        limit = limit or self.config.meta_store.similarity_search.max_results
        max_cosine_distance = (
            max_cosine_distance or self.config.meta_store.similarity_search.max_cosine_distance
        )

        query_vector = self.embedder.encode([query]).squeeze().tolist()

        with self.meta_store.read_session() as session:
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
        with self.meta_store.read_session() as session:
            if not session.exists('roles', name):
                raise ValueError(f"Role '{name}' does not exist.")

        role_path = f'roles/{name}/ROLE.md'
        return self.file_store.load(role_path)

    def get_skill_files(self, name: str) -> dict[str, bytes]:
        """Get all raw files for a skill."""
        # Library skills are already raw bytes in self._library_skills if we store them that way
        # or we need to adapt _get_builtin_skills
        if name in self._library_skills:
            return {fn: obj.content for fn, obj in self._library_skills[name].items()}

        with self.meta_store.read_session() as session:
            if not session.exists('skills', name):
                raise ValueError(f"Skill '{name}' does not exist.")

            skill_data = session.get_one('skills', name, ['files']).to_pylist()[0]

        skill_files_paths = skill_data['files']

        results = {}
        for storage_path in skill_files_paths:
            filename = storage_path.rsplit('/', 1)[-1]
            results[filename] = self.file_store.load(storage_path)

        return results

    def install_skill(self, name: str, local_skill_dir: plb.Path) -> str:
        """Install a skill to a local directory."""
        if not local_skill_dir.is_absolute():
            raise ValueError(f"Path '{local_skill_dir}' must be absolute.")
        if not local_skill_dir.exists():
            raise ValueError(f"Path '{local_skill_dir}' does not exist.")

        # We still need to know where the skill is relative to the root for storage paths
        # but the API should probably just return the files and let the caller decide where they go?
        # No, install_skill is a high-level operation.
        # But it should use the raw file paths.

        with self.meta_store.read_session() as session:
            if not session.exists('skills', name):
                raise ValueError(f"Skill '{name}' does not exist.")
            skill_data = session.get_one('skills', name, ['files']).to_pylist()[0]

        skill_files_paths = skill_data['files']
        skill_md_local_path = None

        for storage_path in skill_files_paths:
            content = self.file_store.load(storage_path)
            filename = storage_path.rsplit('/', 1)[-1]

            # Standardize destination path: skills/name/file -> local_skill_dir/name/file
            relative_path = storage_path.replace('skills/', '', 1)
            dest = local_skill_dir / relative_path

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

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
        tagger = get_tagger(self.embedder)
        template: Template = TemplateFile.validate_python({'path': path, 'type': type})

        # Transaction handling needs to be careful with injected engines
        # Transaction class usually expects to manage the commit/rollback logic

        with Transaction(self.file_store, self.meta_store):
            template.process_template(
                entry=IndexEntry(name=name, description=description, tags=tags or []),
                target_file_store=self.file_store,
                meta_store_engine=self.meta_store,
                embedder=self.embedder,
                tagger=tagger,
            )

    def delete_template(self, name: str, type: personaTypes):
        """Delete a template."""
        with Transaction(self.file_store, self.meta_store):
            with self.meta_store.read_session() as session:  # Check existence
                if not session.exists(type, name):
                    raise ValueError(f"{type.capitalize()} '{name}' does not exist.")

            template_key = f'{type}/{name}'
            for file in self.file_store.glob(f'{template_key}/**/*'):
                if self.file_store.is_dir(file):
                    continue
                self.file_store.delete(cast(str, file))

            self.file_store.delete(template_key, recursive=True)
            self.meta_store.deindex(entry=IndexEntry(name=name, type=type))

    def get_skill_version(self, name: str) -> str:
        """Get the version (UUID) of a skill."""
        with self.meta_store.read_session() as session:
            if not session.exists('skills', name):
                raise ValueError(f"Skill '{name}' not found.")
            result = session.get_one('skills', name, ['uuid']).to_pylist()[0]
            return result['uuid']
