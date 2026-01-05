import os
from typing import cast
import pathlib as plb
import tempfile
import zipfile
import shutil
import logging
from io import BytesIO

import httpx
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from pathlib import Path
from platformdirs import user_data_path

options = ort.SessionOptions()
options.log_severity_level = 3

logger = logging.getLogger('persona.embedder')


def get_embedding_model(
    model_dir: str | plb.Path | None = None, model_name: str = 'model.onnx'
) -> 'FastEmbedder':
    """Get the embedding model

    Args:
        model_dir (str | plb.Path | None, optional): Location of the model directory. Defaults to None.
        model_name (str, optional): Name of the model file. Defaults to 'model.onnx'.

    Returns:
        FastEmbedder: Embedding model instance.
    """
    model_dir = plb.Path(
        model_dir
        or (
            user_data_path('persona', 'jasper_ginn', ensure_exists=True)
            / 'embeddings/minilm-l6-v2-persona-ft-q8'
        )
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    if not sorted(os.listdir(str(model_dir))) == [
        'config.json',
        'model.onnx',
        'model.onnx.data',
        'special_tokens_map.json',
        'tokenizer.json',
        'tokenizer_config.json',
        'vocab.txt',
    ]:
        logger.info('Embedding model not found. Downloading...')
        downloader = EmbeddingDownloader()
        downloader.download()

    return FastEmbedder(model_dir=str(model_dir), model_name=model_name)


class EmbeddingDownloader:
    def __init__(self):
        """If not present, will download the model to the data directory"""
        self._logger = logging.getLogger('persona.embedder.EmbeddingDownloader')
        self._persona_data_dir = user_data_path('persona', 'jasper_ginn', ensure_exists=True)
        self._model_dir = 'embeddings/minilm-l6-v2-persona-ft-q8'
        self._model_url = 'https://github.com/JasperHG90/persona/raw/refs/heads/main/assets/minilm-l6-v2-persona-ft-q8.zip'

    @property
    def model_dir(self) -> plb.Path:
        return self._persona_data_dir / self._model_dir

    def _download_and_unzip(self, url: str, dest: plb.Path) -> None:
        """Download and unzip the model from the given URL to the destination directory."""
        try:
            response = httpx.get(url, follow_redirects=True)
            response.raise_for_status()

            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(BytesIO(response.content)) as z:
                    z.extractall(temp_dir)

                extracted_dir = plb.Path(temp_dir) / 'minilm-l6-v2-persona-ft-q8'

                for item in extracted_dir.iterdir():
                    target_path = dest / item.name
                    if target_path.exists():
                        if target_path.is_dir():
                            shutil.rmtree(target_path)
                        else:
                            target_path.unlink()
                    shutil.move(str(item), str(target_path))
            self._logger.info(f'Model downloaded and extracted to {dest}')

        except httpx.RequestError as e:
            self._logger.error(f'Failed to download model from {url}: {e}')
            raise

    def download(self, force_download: bool = False) -> None:
        """Download the model to the model directory."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._download_and_unzip(self._model_url, self.model_dir)


class FastEmbedder:
    def __init__(self, model_dir: str | plb.Path, model_name: str = 'model.onnx'):
        """Retrieve an embedder instance

        Args:
            model_dir (str | plb.Path): Directory in which the downloaded model is stored.
            model_name (str, optional): Name of the model file. Defaults to 'model.onnx'.
        """
        self.tokenizer: Tokenizer = Tokenizer.from_file(str(Path(model_dir) / 'tokenizer.json'))
        self.tokenizer.enable_padding(pad_id=0, pad_token='[PAD]')
        self.tokenizer.enable_truncation(max_length=512)

        self.session = ort.InferenceSession(
            str(Path(model_dir) / model_name),
            providers=['CPUExecutionProvider'],
            sess_options=options,
        )

    def encode(self, text: list[str]) -> np.ndarray[tuple[int, int], np.dtype[np.float32]]:
        """Retrieve the embedding for a text query.

        Args:
            text (list[str]): Input texts to be embedded.

        Returns:
            np.ndarray: Array containing the embedding for the input text.
        """
        input_ids = []
        attention_mask = []
        for e in self.tokenizer.encode_batch(text):
            input_ids.append(np.array(e.ids, dtype=np.int64))
            attention_mask.append(np.array(e.attention_mask, dtype=np.int64))

        inputs = {
            'input_ids': np.vstack(input_ids),
            'attention_mask': np.vstack(attention_mask),
        }

        outputs = cast(list[np.ndarray], self.session.run(None, inputs))

        return outputs[0]
