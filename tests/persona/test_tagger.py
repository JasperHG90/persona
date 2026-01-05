import gzip
import pathlib as plb
from typing import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from persona.embedder import FastEmbedder
from persona.tagger import (
    TagExtractor,
    TaggingKeywordsProcessor,
    get_tagger,
)


@pytest.fixture
def mock_embedder() -> MagicMock:
    mock = MagicMock(spec=FastEmbedder)
    # Mock encode to return a 384-dimensional vector (standard for the model used)
    mock.encode.return_value = np.zeros((1, 384), dtype=np.float32)
    return mock


@pytest.fixture
def mock_user_data_path(tmp_path: plb.Path) -> Generator[MagicMock, None, None]:
    with patch('persona.tagger.user_data_path') as mock:
        mock.return_value = tmp_path
        yield mock


class TestTaggingKeywordsProcessor:
    def test_parse_keywords(self) -> None:
        # Arrange
        data = b'{"context": "ctx1", "name": "n1"}\n\n{"context": "ctx2", "name": "n2"}'

        # Act
        result = TaggingKeywordsProcessor._parse_keywords(data)

        # Assert
        assert len(result) == 2
        assert result[0] == {'context': 'ctx1', 'name': 'n1'}
        assert result[1] == {'context': 'ctx2', 'name': 'n2'}

    def test_download_keywords(self, mock_embedder: MagicMock) -> None:
        # Arrange
        processor = TaggingKeywordsProcessor(model=mock_embedder)
        raw_data = b'{"context": "ctx1", "name": "n1"}'
        gzipped_data = gzip.compress(raw_data)

        with patch('httpx.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = gzipped_data
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            # Act
            result = processor._download_keywords()

            # Assert
            assert result == [{'context': 'ctx1', 'name': 'n1'}]
            mock_get.assert_called_once_with(processor._vocab_url, follow_redirects=True)

    def test_embed_keywords(self, mock_embedder: MagicMock) -> None:
        # Arrange
        processor = TaggingKeywordsProcessor(model=mock_embedder)
        keywords = [{'context': 'ctx1'}, {'context': 'ctx2'}]
        # Mock embedder to return two vectors
        mock_embedder.encode.return_value = np.array([[0.1] * 384, [0.2] * 384], dtype=np.float32)

        # Act
        result = processor._embed_keywords(keywords)

        # Assert
        assert len(result) == 2
        assert result[0]['embedding'] == pytest.approx([0.1] * 384)
        assert result[1]['embedding'] == pytest.approx([0.2] * 384)
        mock_embedder.encode.assert_called_once_with(['ctx1', 'ctx2'])

    def test_save_keywords(
        self, mock_embedder: MagicMock, mock_user_data_path: MagicMock, tmp_path: plb.Path
    ) -> None:
        # Arrange
        processor = TaggingKeywordsProcessor(model=mock_embedder)
        keywords = [{'context': 'ctx1', 'embedding': [0.1] * 384}]

        # Act
        processor._save_keywords(keywords)

        # Assert
        expected_path = tmp_path / 'tagging' / 'keywords_embedded.parquet'
        assert expected_path.exists()
        table = pq.read_table(expected_path)
        assert table.to_pylist() == keywords

    def test_process_flow(self, mock_embedder: MagicMock, mock_user_data_path: MagicMock) -> None:
        # Arrange
        processor = TaggingKeywordsProcessor(model=mock_embedder)

        with (
            patch.object(processor, '_download_keywords') as mock_download,
            patch.object(processor, '_embed_keywords') as mock_embed,
            patch.object(processor, '_save_keywords') as mock_save,
        ):
            mock_download.return_value = [{'k': 'v'}]
            mock_embed.return_value = [{'k': 'v', 'emb': []}]

            # Act
            processor.process()

            # Assert
            mock_download.assert_called_once()
            mock_embed.assert_called_once_with([{'k': 'v'}])
            mock_save.assert_called_once_with([{'k': 'v', 'emb': []}])


class TestGetTagger:
    def test_get_tagger_caching(
        self, mock_embedder: MagicMock, mock_user_data_path: MagicMock, tmp_path: plb.Path
    ) -> None:
        # Arrange
        tagging_dir = tmp_path / 'tagging'
        tagging_dir.mkdir(parents=True)
        parquet_file = tagging_dir / 'keywords_embedded.parquet'
        parquet_file.touch()

        with (
            patch('persona.tagger.TaggingKeywordsProcessor') as mock_proc_cls,
            patch('persona.tagger.TagExtractor') as mock_extractor_cls,
        ):
            # Act
            get_tagger(model=mock_embedder)

            # Assert
            mock_proc_cls.assert_not_called()
            mock_extractor_cls.assert_called_once_with(model=mock_embedder)

    def test_get_tagger_triggers_process(
        self, mock_embedder: MagicMock, mock_user_data_path: MagicMock, tmp_path: plb.Path
    ) -> None:
        # Arrange
        # Ensure file does NOT exist

        with (
            patch('persona.tagger.TaggingKeywordsProcessor') as mock_proc_cls,
            patch('persona.tagger.TagExtractor') as mock_extractor_cls,
        ):
            # Act
            get_tagger(model=mock_embedder)

            # Assert
            mock_proc_cls.assert_called_once_with(model=mock_embedder)
            mock_proc_cls.return_value.process.assert_called_once()
            mock_extractor_cls.assert_called_once_with(model=mock_embedder)


class TestTagExtractor:
    def test_init_raises_if_missing_file(
        self, mock_embedder: MagicMock, mock_user_data_path: MagicMock
    ) -> None:
        # Arrange
        # No file in tmp_path

        # Act & Assert
        with pytest.raises(FileNotFoundError, match='Embedded keywords file not found'):
            TagExtractor(model=mock_embedder)

    def test_extract_tags(
        self, mock_embedder: MagicMock, mock_user_data_path: MagicMock, tmp_path: plb.Path
    ) -> None:
        # Arrange
        tagging_dir = tmp_path / 'tagging'
        tagging_dir.mkdir(parents=True)
        vocab_path = tagging_dir / 'keywords_embedded.parquet'

        # Create a small vocab with known vectors
        # Vector [1, 0, ...] will have high similarity with [1, 0, ...]
        vec_1 = [1.0] + [0.0] * 383
        vec_2 = [0.0, 1.0] + [0.0, 0.0] * 191
        keywords = [
            {'name': 'Python', 'facet': 'Technology', 'embedding': vec_1},
            {'name': 'Senior', 'facet': 'Seniority', 'embedding': vec_2},
        ]
        table = pa.Table.from_pylist(keywords)
        pq.write_table(table, vocab_path)

        # Mock embedder to return vec_1 for the first query and vec_2 for the second
        mock_embedder.encode.return_value = np.array([vec_1, vec_2], dtype=np.float32)

        extractor = TagExtractor(model=mock_embedder)

        # Act
        results = extractor.extract_tags(
            ids=['id1', 'id2'], texts=['python developer', 'senior level']
        )

        # Assert
        assert 'id1' in results
        assert 'Python' in results['id1']
        assert 'id2' in results
        assert 'Senior' in results['id2']
