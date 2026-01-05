import zipfile
from io import BytesIO
from typing import Generator
from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest
from tokenizers import Encoding

from persona.embedder import EmbeddingDownloader, FastEmbedder, get_embedding_model


@pytest.fixture
def mock_user_data_path() -> Generator[MagicMock, None, None]:
    with patch('persona.embedder.user_data_path') as mock:
        yield mock


@pytest.fixture
def mock_httpx_get() -> Generator[MagicMock, None, None]:
    with patch('httpx.get') as mock:
        yield mock


@pytest.fixture
def mock_tokenizer() -> Generator[MagicMock, None, None]:
    with patch('persona.embedder.Tokenizer') as mock:
        # Setup default mock behavior
        instance = mock.from_file.return_value
        instance.encode_batch.return_value = [
            MagicMock(spec=Encoding, ids=[1, 2], attention_mask=[1, 1])
        ]
        yield mock


@pytest.fixture
def mock_ort() -> Generator[MagicMock, None, None]:
    with patch('persona.embedder.ort') as mock:
        # Setup default mock behavior
        session = mock.InferenceSession.return_value
        # Return a dummy embedding vector of size 384
        session.run.return_value = [np.zeros((1, 384), dtype=np.float32)]
        yield mock


class TestGetEmbeddingModel:
    def test_model_exists(
        self,
        mock_user_data_path: MagicMock,
        mock_tokenizer: MagicMock,
        mock_ort: MagicMock,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        # Arrange
        # Create a fake model directory structure
        model_dir = tmp_path / 'embeddings' / 'minilm-l6-v2-persona-ft-q8'
        model_dir.mkdir(parents=True)
        required_files = [
            'config.json',
            'model.onnx',
            'model.onnx.data',
            'special_tokens_map.json',
            'tokenizer.json',
            'tokenizer_config.json',
            'vocab.txt',
        ]
        for f in required_files:
            (model_dir / f).touch()

        mock_user_data_path.return_value = tmp_path

        # Act
        with patch('persona.embedder.EmbeddingDownloader') as mock_downloader:
            embedder = get_embedding_model()

            # Assert
            mock_downloader.assert_not_called()
            assert isinstance(embedder, FastEmbedder)
            mock_tokenizer.from_file.assert_called_once()
            mock_ort.InferenceSession.assert_called_once()

    def test_model_missing_triggers_download(
        self,
        mock_user_data_path: MagicMock,
        mock_tokenizer: MagicMock,
        mock_ort: MagicMock,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        # Arrange
        mock_user_data_path.return_value = tmp_path
        # Don't create files, so it looks like they are missing

        # Act
        with patch('persona.embedder.EmbeddingDownloader') as mock_downloader_cls:
            mock_downloader_instance = mock_downloader_cls.return_value

            get_embedding_model()

            # Assert
            mock_downloader_cls.assert_called_once()
            mock_downloader_instance.download.assert_called_once()


class TestEmbeddingDownloader:
    def test_download_success(
        self,
        mock_user_data_path: MagicMock,
        mock_httpx_get: MagicMock,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        # Arrange
        mock_user_data_path.return_value = tmp_path

        # Create a valid zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # The code expects files to be inside a folder named 'minilm-l6-v2-persona-ft-q8'
            zf.writestr('minilm-l6-v2-persona-ft-q8/model.onnx', b'dummy content')

        mock_response = MagicMock()
        mock_response.content = zip_buffer.getvalue()
        mock_httpx_get.return_value = mock_response

        downloader = EmbeddingDownloader()

        # Act
        downloader.download(force_download=True)

        # Assert
        target_dir = tmp_path / 'embeddings/minilm-l6-v2-persona-ft-q8'
        assert target_dir.exists()
        assert (target_dir / 'model.onnx').exists()
        assert (target_dir / 'model.onnx').read_bytes() == b'dummy content'

    def test_download_error(
        self,
        mock_user_data_path: MagicMock,
        mock_httpx_get: MagicMock,
    ) -> None:
        # Arrange
        mock_httpx_get.side_effect = httpx.RequestError('Network error')
        downloader = EmbeddingDownloader()

        # Act & Assert
        with pytest.raises(httpx.RequestError):
            downloader.download(force_download=True)


class TestFastEmbedder:
    def test_init(self, mock_tokenizer: MagicMock, mock_ort: MagicMock) -> None:
        # Arrange
        model_dir = '/tmp/model'

        # Act
        FastEmbedder(model_dir=model_dir)

        # Assert
        mock_tokenizer.from_file.assert_called_once_with('/tmp/model/tokenizer.json')
        mock_ort.InferenceSession.assert_called_once()

        # Check tokenizer configuration
        tokenizer_instance = mock_tokenizer.from_file.return_value
        tokenizer_instance.enable_padding.assert_called_once_with(pad_id=0, pad_token='[PAD]')
        tokenizer_instance.enable_truncation.assert_called_once_with(max_length=512)

    def test_encode(self, mock_tokenizer: MagicMock, mock_ort: MagicMock) -> None:
        # Arrange
        embedder = FastEmbedder(model_dir='/tmp/model')

        # Setup specific mock returns for this test
        tokenizer_instance = mock_tokenizer.from_file.return_value

        # Create mock encodings
        mock_encoding = MagicMock(spec=Encoding)
        mock_encoding.ids = [101, 202, 303]
        mock_encoding.attention_mask = [1, 1, 1]
        tokenizer_instance.encode_batch.return_value = [mock_encoding]

        session_instance = mock_ort.InferenceSession.return_value
        expected_output = np.random.rand(1, 384).astype(np.float32)
        session_instance.run.return_value = [expected_output]

        # Act
        result = embedder.encode(['test text'])

        # Assert
        tokenizer_instance.encode_batch.assert_called_once_with(['test text'])

        # Verify inputs to session.run
        _, kwargs = session_instance.run.call_args
        # The first arg is None, second is inputs dict
        # Actually session.run(None, inputs) -> args[0] is None, args[1] is dict
        call_args = session_instance.run.call_args
        assert call_args[0][0] is None
        input_feed = call_args[0][1]

        assert 'input_ids' in input_feed
        assert 'attention_mask' in input_feed
        assert input_feed['input_ids'].shape == (1, 3)
        assert input_feed['attention_mask'].shape == (1, 3)

        assert np.array_equal(result, expected_output)
