from typing import cast
import logging
import gzip

import duckdb
import orjson
import httpx
from platformdirs import user_data_path
import pyarrow as pa
from pyarrow import parquet as pq

from persona.embedder import FastEmbedder

logger = logging.getLogger('persona.tagger')


def get_tagger(model: FastEmbedder) -> 'TagExtractor':
    """Get the embedding model

    Args:
        model_dir (str | plb.Path | None, optional): Location of the model directory. Defaults to None.
        model_name (str, optional): Name of the model file. Defaults to 'model.onnx'.
    """
    keywords_dir = user_data_path('persona', 'jasper_ginn', ensure_exists=True) / 'tagging'
    keywords_dir.mkdir(parents=True, exist_ok=True)
    if not (keywords_dir / 'keywords_embedded.parquet').exists():
        logger.info('Downloading and processing tagging keywords...')
        processor = TaggingKeywordsProcessor(model=model)
        processor.process()

    return TagExtractor(model=model)


class TaggingKeywordsProcessor:
    def __init__(self, model: FastEmbedder) -> None:
        """If not present, will download the model to the data directory"""
        self._logger = logging.getLogger('persona.tagging.TaggingKeywordsProcessor')
        self._persona_data_dir = user_data_path('persona', 'jasper_ginn', ensure_exists=True)
        self._vocab_dir = self._persona_data_dir / 'tagging'
        self._vocab_dir.mkdir(parents=True, exist_ok=True)
        self._vocab_url = 'https://raw.githubusercontent.com/JasperHG90/persona/refs/heads/main/assets/kw_all.jsonl.gz'
        self._model = model

    @staticmethod
    def _parse_keywords(content: bytes) -> list[dict[str, str]]:
        vocab = []
        for r in content.decode('utf-8').split('\n'):
            if r == '':
                continue
            vocab.append(orjson.loads(r.strip().encode('utf-8')))
        return vocab

    def _download_keywords(self) -> list[dict[str, str]]:
        resp = httpx.get(self._vocab_url, follow_redirects=True)
        resp.raise_for_status()
        return self._parse_keywords(gzip.decompress(resp.content))

    def _embed_keywords(self, keywords: list[dict[str, str]]) -> list[dict[str, str]]:
        texts = [cast(str, v['context']) for v in keywords]
        embeddings = self._model.encode(texts)
        for i, v in enumerate(keywords):
            v['embedding'] = embeddings[i].tolist()
        return keywords

    def _save_keywords(self, keywords: list[dict[str, str]]) -> None:
        vocab_path = self._vocab_dir / 'keywords_embedded.parquet'
        table = pa.Table.from_pylist(keywords)
        pq.write_table(table, vocab_path)
        self._logger.info(f'Saved embedded keywords to {vocab_path}')

    def process(self) -> None:
        keywords = self._download_keywords()
        embedded_keywords = self._embed_keywords(keywords)
        self._save_keywords(embedded_keywords)


class TagExtractor:
    def __init__(self, model: FastEmbedder) -> None:
        """If not present, will download the model to the data directory"""
        self._logger = logging.getLogger('persona.tagging.TagExtractor')
        self._persona_data_dir = user_data_path('persona', 'jasper_ginn', ensure_exists=True)
        self._vocab_dir = self._persona_data_dir / 'tagging'
        self._vocab_path = self._vocab_dir / 'keywords_embedded.parquet'
        if not self._vocab_path.exists():
            raise FileNotFoundError(
                f'Embedded keywords file not found at {self._vocab_path}. Please run TaggingKeywordsProcessor first.'
            )
        self._model = model
        self._con = duckdb.connect(':memory:')

    @property
    def _sql(self) -> str:
        return f"""
        WITH matched_taxonomy AS (
            SELECT
                i.input_id,
                t.name,
                t.facet,
                ROUND(array_cosine_similarity(t.embedding::FLOAT[384], i.query_vec::FLOAT[384])::DOUBLE, 3) as score,
                row_number() OVER (PARTITION BY i.input_id, t.facet ORDER BY score DESC) as rank
            FROM read_parquet('{self._vocab_path}') t
            CROSS JOIN queries i
            QUALIFY
                (facet = 'Seniority' AND rank <= 1 AND score >= 0.4)
                OR (facet = 'Soft Skill' AND rank <= 2 AND score >= 0.4)
                OR (facet = 'Hard Skill' AND rank <= 2 AND score >= 0.35)
                OR (facet = 'Methodology' AND rank <= 2 AND score >= 0.4)
                OR (facet = 'Role' AND rank <= 1 AND score >= 0.4)
                OR (facet = 'Domain' AND rank <= 2 AND score >= 0.4)
                OR (facet = 'Technology' AND rank <= 3 AND score >= 0.7)
        ),
        unique_tags AS (
            -- Deduplicate: Keep only the highest score for each tag per input
            SELECT
                input_id,
                name,
                MAX(score) as best_score
            FROM matched_taxonomy
            GROUP BY input_id, name
        )
        SELECT
            input_id,
            -- Aggregate unique tags into a list, sorted by the highest match score
            list(name ORDER BY best_score DESC) as tags
        FROM unique_tags
        GROUP BY input_id
        ORDER BY input_id;
        """

    def extract_tags(self, ids: list[str], texts: list[str]) -> dict[str, list[str]]:
        # NB: used in sql query
        queries = pa.Table.from_pydict({'id': ids, 'query_vec': self._model.encode(texts).tolist()})  # noqa
        return {
            r['input_id']: r['tags']
            for r in self._con.execute(self._sql).fetch_arrow_table().to_pylist()
        }
