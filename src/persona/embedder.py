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
from platformdirs import user_data_dir


class EmbeddingDownloader:
    
    def __init__(self):
        self._logger = logging.getLogger(f'persona.embedder.EmbeddingDownloader')
        self._persona_data_dir = plb.Path(user_data_dir("persona", "jasper_ginn", ensure_exists=True))
        self._model_dir = "embeddings/minilm-l6-v2-quantized"
        self._model_url = ""
        
    @property
    def model_dir(self) -> plb.Path:
        return self._persona_data_dir / self._model_dir
    
    def _download_and_unzip(self, url: str, dest: plb.Path) -> None:
        try:
            response = httpx.get(url, follow_redirects=True)
            response.raise_for_status()

            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(BytesIO(response.content)) as z:
                    z.extractall(temp_dir)

                extracted_dir = plb.Path(temp_dir) / self._model_dir

                shutil.move(str(extracted_dir), str(dest))

        except httpx.RequestError as e:
            self._logger.error(f"Failed to download model from {url}: {e}")
            raise
        
    def download(self, force_download: bool = False) -> None:
        if not self.model_dir.exists() or force_download:
            self.model_dir.mkdir(parents=True, exist_ok=True)
        self._download_and_unzip(self._model_url, self.model_dir)


class FastEmbedder:
    def __init__(self, model_dir: str | plb.Path, model_name: str = "model.onnx"):
        self.tokenizer: Tokenizer = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self.tokenizer.enable_truncation(max_length=512)

        self.session = ort.InferenceSession(
            str(Path(model_dir) / model_name), 
            providers=["CPUExecutionProvider"]
        )

    def encode(self, text):
        enc = self.tokenizer.encode(text)
        inputs = {
            "input_ids": np.array([enc.ids], dtype=np.int64),
            "attention_mask": np.array([enc.attention_mask], dtype=np.int64),
        }

        outputs = self.session.run(None, inputs)
        
        # NB: mean pooling is standard for sentence transformers I believe
        token_embeddings = cast(np.ndarray, outputs[0])
        mask = np.expand_dims(inputs["attention_mask"], -1)
        embeddings = cast(np.ndarray, np.sum(token_embeddings * mask, 1) / np.maximum(mask.sum(1), 1e-9))
        
        norm = cast(np.ndarray, np.linalg.norm(embeddings, axis=1, keepdims=True))
        return (embeddings / norm).flatten()
