import pathlib as plb
from unittest.mock import MagicMock, patch
import pytest
import frontmatter
import numpy as np

from persona.api import PersonaAPI
from persona.storage import BaseFileStore, CursorLikeMetaStoreEngine
from persona.embedder import FastEmbedder
from persona.models import SkillFile


@pytest.fixture
def mock_config() -> MagicMock:
    # Use a generic MagicMock to avoid strict spec issues with Pydantic fields
    config = MagicMock()
    # Setup the nested structure required by api.py
    config.meta_store.similarity_search.max_results = 5
    config.meta_store.similarity_search.max_cosine_distance = 0.5
    return config


@pytest.fixture
def mock_file_store() -> MagicMock:
    return MagicMock(spec=BaseFileStore)


@pytest.fixture
def mock_meta_store() -> MagicMock:
    meta = MagicMock(spec=CursorLikeMetaStoreEngine)
    meta._bootstrapped = True
    # Mock context managers for read/write sessions
    mock_session = MagicMock()
    meta.read_session.return_value.__enter__.return_value = mock_session
    meta.open.return_value.__enter__.return_value = mock_session
    return meta


@pytest.fixture
def mock_embedder() -> MagicMock:
    embedder = MagicMock(spec=FastEmbedder)
    # Mock encode to return a generic vector
    embedder.encode.return_value = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
    return embedder


@pytest.fixture
def api(
    mock_config: MagicMock,
    mock_meta_store: MagicMock,
    mock_file_store: MagicMock,
    mock_embedder: MagicMock,
) -> PersonaAPI:
    return PersonaAPI(
        config=mock_config,
        meta_store=mock_meta_store,
        file_store=mock_file_store,
        embedder=mock_embedder,
    )


class TestInitialization:
    def test_init_success(self, api: PersonaAPI) -> None:
        assert isinstance(api, PersonaAPI)
        assert api._embedder is not None
        assert api._file_store is not None

    def test_init_raises_if_not_bootstrapped(self, mock_config: MagicMock) -> None:
        not_bootstrapped_meta = MagicMock(spec=CursorLikeMetaStoreEngine)
        not_bootstrapped_meta._bootstrapped = False

        with pytest.raises(ValueError, match='must already be bootstrapped'):
            PersonaAPI(config=mock_config, meta_store=not_bootstrapped_meta)

    def test_requires_embedder_raises(
        self, mock_config: MagicMock, mock_meta_store: MagicMock
    ) -> None:
        api = PersonaAPI(config=mock_config, meta_store=mock_meta_store, embedder=None)
        with pytest.raises(ValueError, match='Embedder instance is required'):
            api._requires_embedder()

    def test_requires_file_store_raises(
        self, mock_config: MagicMock, mock_meta_store: MagicMock
    ) -> None:
        api = PersonaAPI(config=mock_config, meta_store=mock_meta_store, file_store=None)
        with pytest.raises(ValueError, match='File store instance is required'):
            api._requires_file_store()


class TestListingAndSearch:
    @pytest.mark.parametrize('type_val', ['roles', 'skills'])
    def test_list_templates(
        self, api: PersonaAPI, mock_meta_store: MagicMock, type_val: str
    ) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        expected_results = [{'name': 'test1'}]
        mock_session.get_many.return_value.to_pylist.return_value = expected_results

        # Act
        results = api.list_templates(type=type_val, columns=['name'])

        # Assert
        assert results == expected_results
        mock_session.get_many.assert_called_once_with(table_name=type_val, column_filter=['name'])

    def test_search_templates(
        self, api: PersonaAPI, mock_meta_store: MagicMock, mock_embedder: MagicMock
    ) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        expected_results = [{'name': 'test1', 'score': 0.9}]
        mock_session.search.return_value.to_pylist.return_value = expected_results

        # Act
        results = api.search_templates(query='test query', type='roles', columns=['name'])

        # Assert
        assert results == expected_results
        mock_embedder.encode.assert_called_once_with(['test query'])
        mock_session.search.assert_called_once()
        # Verify default limits from config were used
        call_kwargs = mock_session.search.call_args.kwargs
        assert call_kwargs['limit'] == 5
        assert call_kwargs['max_cosine_distance'] == 0.5


class TestContentRetrieval:
    def test_get_definition_success(
        self, api: PersonaAPI, mock_meta_store: MagicMock, mock_file_store: MagicMock
    ) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = True
        mock_file_store.load.return_value = b'role content'

        # Act
        content = api.get_definition('my_role', 'roles')

        # Assert
        assert content == b'role content'
        mock_file_store.load.assert_called_once_with('roles/my_role/ROLE.md')

    def test_get_definition_not_found(self, api: PersonaAPI, mock_meta_store: MagicMock) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = False

        # Act & Assert
        with pytest.raises(ValueError, match="Role 'my_role' does not exist"):
            api.get_definition('my_role', 'roles')

    def test_get_skill_files_library(
        self, mock_config: MagicMock, mock_meta_store: MagicMock
    ) -> None:
        # Arrange
        lib_skills = {
            'lib_skill': {
                'script.py': SkillFile(
                    content=b"print('hi')",
                    name='script.py',
                    storage_file_path='p/script.py',
                    extension='.py',
                )
            }
        }
        api = PersonaAPI(
            config=mock_config,
            meta_store=mock_meta_store,
            file_store=MagicMock(),
            library_skills=lib_skills,
        )

        # Act
        files = api.get_skill_files('lib_skill')

        # Assert
        assert files == {'script.py': b"print('hi')"}
        # Should not hit meta_store for library skills
        mock_meta_store.read_session.assert_not_called()

    def test_get_skill_files_local(
        self, api: PersonaAPI, mock_meta_store: MagicMock, mock_file_store: MagicMock
    ) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = True
        mock_session.get_one.return_value.to_pylist.return_value = [
            {'files': ['skills/my_skill/s.py']}
        ]
        mock_file_store.load.return_value = b'code'

        # Act
        files = api.get_skill_files('my_skill')

        # Assert
        assert files == {'s.py': b'code'}
        mock_file_store.load.assert_called_with('skills/my_skill/s.py')

    def test_get_skill_files_not_found(self, api: PersonaAPI, mock_meta_store: MagicMock) -> None:
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = False

        with pytest.raises(ValueError, match="Skill 'missing' does not exist"):
            api.get_skill_files('missing')


class TestSkillInstallation:
    def test_install_skill_validation(self, api: PersonaAPI) -> None:
        with pytest.raises(ValueError, match='must be absolute'):
            api.install_skill('skill', plb.Path('relative/path'))

        with pytest.raises(ValueError, match='does not exist'):
            api.install_skill('skill', plb.Path('/abs/nonexistent'))

    def test_install_skill_success(
        self,
        api: PersonaAPI,
        mock_meta_store: MagicMock,
        mock_file_store: MagicMock,
        tmp_path: plb.Path,
    ) -> None:
        # Arrange
        target_dir = tmp_path / 'skills'
        target_dir.mkdir()

        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = True
        mock_session.get_one.return_value.to_pylist.return_value = [
            {'name': 'test_skill', 'files': ['skills/test_skill/script.py'], 'uuid': 'uuid-123'}
        ]

        # Mock file loading
        def load_side_effect(path: str) -> bytes:
            if path.endswith('SKILL.md'):
                return b'---\nname: test_skill\n---\n'
            return b"print('hello')"

        mock_file_store.load.side_effect = load_side_effect

        # Act
        # Note: SKILL.md is implicitly added in _skill_files logic
        result_path = api.install_skill('test_skill', target_dir)

        # Assert
        assert result_path == str(target_dir / 'test_skill' / 'SKILL.md')
        assert (target_dir / 'test_skill' / 'script.py').exists()
        assert (target_dir / 'test_skill' / 'SKILL.md').exists()

        # Check UUID injection in SKILL.md
        with open(result_path, 'r') as f:
            content = frontmatter.load(f)
            assert content.metadata['metadata']['version'] == 'uuid-123'


class TestPublishAndDelete:
    def test_publish_template(
        self, api: PersonaAPI, mock_meta_store: MagicMock, mock_file_store: MagicMock
    ) -> None:
        # Arrange
        path = plb.Path('/tmp/template.md')

        with (
            patch('persona.api.Transaction') as mock_transaction,
            patch('persona.api.TemplateFile.validate_python') as mock_validate,
            patch('persona.api.get_tagger') as mock_get_tagger,
        ):
            mock_template = MagicMock()
            mock_validate.return_value = mock_template

            # Act
            api.publish_template(path, 'roles', name='New Role')

            # Assert
            mock_validate.assert_called_once()
            mock_transaction.assert_called_once_with(mock_file_store, mock_meta_store)
            mock_template.process_template.assert_called_once()

            # Verify dependencies passed to process_template
            call_kwargs = mock_template.process_template.call_args.kwargs
            assert call_kwargs['target_file_store'] == mock_file_store
            assert call_kwargs['meta_store_engine'] == mock_meta_store
            assert call_kwargs['embedder'] == api._embedder
            assert call_kwargs['tagger'] == mock_get_tagger.return_value

    def test_delete_template(
        self, api: PersonaAPI, mock_meta_store: MagicMock, mock_file_store: MagicMock
    ) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = True

        # Mock glob to return some files
        mock_file_store.glob.return_value = ['roles/del_role/ROLE.md', 'roles/del_role/']
        mock_file_store.is_dir.side_effect = lambda p: p.endswith('/')

        with patch('persona.api.Transaction') as mock_transaction:
            # Act
            api.delete_template('del_role', 'roles')

            # Assert
            mock_transaction.assert_called_once()
            # Verify recursive delete calls
            mock_file_store.delete.assert_any_call('roles/del_role/ROLE.md')
            mock_file_store.delete.assert_any_call('roles/del_role', recursive=True)
            mock_meta_store.deindex.assert_called_once()


class TestMetadata:
    def test_get_skill_version(self, api: PersonaAPI, mock_meta_store: MagicMock) -> None:
        # Arrange
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = True
        mock_session.get_one.return_value.to_pylist.return_value = [{'uuid': 'v1'}]

        # Act
        version = api.get_skill_version('my_skill')

        # Assert
        assert version == 'v1'
        mock_session.get_one.assert_called_once_with('skills', 'my_skill', ['uuid'])

    def test_get_skill_version_not_found(self, api: PersonaAPI, mock_meta_store: MagicMock) -> None:
        mock_session = mock_meta_store.read_session.return_value.__enter__.return_value
        mock_session.exists.return_value = False

        with pytest.raises(ValueError, match="Skill 'missing' not found"):
            api.get_skill_version('missing')
