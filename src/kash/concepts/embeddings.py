from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path
from typing import TypeAlias, cast

import pandas as pd
from litellm import embedding
from litellm.types.utils import EmbeddingResponse
from pydantic.dataclasses import dataclass
from strif import abbrev_list

from kash.config.logger import get_logger
from kash.llm_utils.llms import DEFAULT_EMBEDDING_MODEL

log = get_logger(__name__)


BATCH_SIZE = 1024

Key: TypeAlias = str

KeyVal: TypeAlias = tuple[Key, str]
"""
A key-value pair where the key is a unique identifier (such as the path)
and the value is the text to embed.
"""


@dataclass
class Embeddings:
    """
    Embedded string values. Each string value has a unique key (e.g. its id or title or for
    small texts, the text itself).
    """

    data: dict[Key, tuple[str, list[float]]]
    """Mapping of key to text and embedding."""

    def as_iterable(self) -> Iterable[tuple[Key, str, list[float]]]:
        return ((key, text, emb) for key, (text, emb) in self.data.items())

    def as_df(self) -> pd.DataFrame:
        keys, texts, embeddings = zip(
            *[(key, text, emb) for key, (text, emb) in self.data.items()], strict=False
        )
        return pd.DataFrame(
            {
                "key": keys,
                "text": texts,
                "embedding": embeddings,
            }
        )

    def __getitem__(self, key: Key) -> tuple[str, list[float]]:
        if key in self.data:
            return self.data[key]
        else:
            raise KeyError(f"Key '{key}' not found in embeddings")

    @classmethod
    def embed(cls, keyvals: list[KeyVal], model=DEFAULT_EMBEDDING_MODEL) -> Embeddings:
        data = {}
        log.message(
            "Embedding %d texts (model %s, batch size %s)…",
            len(keyvals),
            model.litellm_name,
            BATCH_SIZE,
        )
        for batch_start in range(0, len(keyvals), BATCH_SIZE):
            batch_end = batch_start + BATCH_SIZE
            batch = keyvals[batch_start:batch_end]
            keys = [kv[0] for kv in batch]
            texts = [kv[1] for kv in batch]

            response: EmbeddingResponse = cast(
                EmbeddingResponse, embedding(model=model.litellm_name, input=texts)
            )
            if not response.data:
                raise ValueError("No embedding response data")

            batch_embeddings = [e["embedding"] for e in response.data]
            data.update(
                {
                    key: (text, emb)
                    for key, text, emb in zip(keys, texts, batch_embeddings, strict=False)
                }
            )

            log.info(
                "Embedded batch %d-%d: %s",
                batch_start,
                batch_end,
                abbrev_list(texts),
            )

        return cls(data=data)

    def to_csv(self, path: Path) -> None:
        self.as_df().to_csv(path, index=False)

    @classmethod
    def read_from_csv(cls, path: Path) -> Embeddings:
        df = pd.read_csv(path)
        df["embedding"] = df["embedding"].apply(ast.literal_eval)
        data = {row["key"]: (row["text"], row["embedding"]) for _, row in df.iterrows()}
        return cls(data=data)  # pyright: ignore

    def to_npz(self, path: Path) -> None:
        """Save embeddings in numpy's compressed format."""
        import numpy as np

        keys: list[Key] = list(self.data.keys())
        texts: list[str] = [self.data[k][0] for k in keys]
        embeddings = np.array([self.data[k][1] for k in keys])
        np.savez_compressed(path, keys=keys, texts=texts, embeddings=embeddings)

    @classmethod
    def read_from_npz(cls, path: Path) -> Embeddings:
        """Load embeddings from numpy's compressed format."""
        import numpy as np

        with np.load(path) as data:
            loaded_data = {
                k: (t, e.tolist())
                for k, t, e in zip(data["keys"], data["texts"], data["embeddings"], strict=False)
            }
        return cls(data=loaded_data)

    def __str__(self) -> str:
        dims = -1 if len(self.data) == 0 else len(next(iter(self.data))[1])
        return f"Embeddings({len(self.data)} items, {dims} dimensions)"
