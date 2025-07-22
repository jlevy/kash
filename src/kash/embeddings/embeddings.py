from __future__ import annotations

import ast
import json
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

import pandas as pd
from pydantic.dataclasses import dataclass
from strif import abbrev_list

from kash.config.logger import get_logger
from kash.llm_utils.init_litellm import init_litellm
from kash.llm_utils.llms import DEFAULT_EMBEDDING_MODEL, EmbeddingModel

if TYPE_CHECKING:
    from pandas import DataFrame

log = get_logger(__name__)


BATCH_SIZE: int = 1024

Key: TypeAlias = str


@dataclass(frozen=True)
class EmbValue:
    emb_text: str
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class KeyVal:
    """
    A key-value pair where the key is a unique identifier (such as the path)
    and the value is the text to embed and any additional data.
    """

    key: Key
    value: EmbValue


@dataclass
class Embeddings:
    """
    Embedded string values. Each string value has a unique key (e.g. its id or title or for
    small texts, the text itself).
    """

    data: dict[Key, tuple[EmbValue, list[float]]]
    """Mapping of key to EmbValue and embedding."""

    def as_iterable(self) -> Iterable[tuple[Key, EmbValue, list[float]]]:
        return ((key, emb_value, emb) for key, (emb_value, emb) in self.data.items())

    def as_df(self) -> DataFrame:
        from pandas import DataFrame

        if not self.data:
            return DataFrame({"key": [], "text": [], "data": [], "embedding": []})

        items = [(key, emb_value, emb) for key, (emb_value, emb) in self.data.items()]
        keys, emb_values, embeddings = zip(*items, strict=False)

        return DataFrame(
            {
                "key": list(keys),
                "text": [ev.emb_text for ev in emb_values],
                "data": [ev.data for ev in emb_values],
                "embedding": list(embeddings),
            }
        )

    def __getitem__(self, key: Key) -> tuple[EmbValue, list[float]]:
        if key in self.data:
            return self.data[key]
        else:
            raise KeyError(f"Key '{key}' not found in embeddings")

    @classmethod
    def embed(
        cls, keyvals: list[KeyVal], model: EmbeddingModel = DEFAULT_EMBEDDING_MODEL
    ) -> Embeddings:
        from litellm import embedding

        init_litellm()

        data: dict[Key, tuple[EmbValue, list[float]]] = {}
        log.info(
            "Embedding %d texts (model %s, batch size %s)…",
            len(keyvals),
            model.litellm_name,
            BATCH_SIZE,
        )
        for batch_start in range(0, len(keyvals), BATCH_SIZE):
            batch_end: int = batch_start + BATCH_SIZE
            batch: list[KeyVal] = keyvals[batch_start:batch_end]
            keys: list[Key] = [kv.key for kv in batch]
            texts: list[str] = [kv.value.emb_text for kv in batch]

            response = embedding(model=model.litellm_name, input=texts)

            if not response.data:
                raise ValueError("No embedding response data")

            batch_embeddings: list[list[float]] = [e["embedding"] for e in response.data]
            data.update(
                {
                    key: (emb_value, emb)
                    for key, emb_value, emb in zip(
                        keys, [kv.value for kv in batch], batch_embeddings, strict=False
                    )
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
        import pandas as pd

        df: pd.DataFrame = pd.read_csv(path)
        df["embedding"] = df["embedding"].apply(ast.literal_eval)

        # Handle missing data column just in case.
        if "data" in df.columns:
            df["data"] = df["data"].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else None)
        else:
            df["data"] = None

        data: dict[Key, tuple[EmbValue, list[float]]] = {}
        for _, row in df.iterrows():
            key = str(row["key"])
            text = str(row["text"])
            embedding = list(row["embedding"])
            # Type-safe handling of data column
            raw_data = row["data"] if "data" in df.columns else None
            data_value: dict[str, Any] | None = (
                raw_data if isinstance(raw_data, dict) or raw_data is None else None
            )

            data[key] = (
                EmbValue(emb_text=text, data=data_value),
                embedding,
            )

        return cls(data=data)

    def to_npz(self, path: Path) -> None:
        """Save embeddings in numpy's compressed format."""
        import numpy as np

        keys: list[Key] = list(self.data.keys())
        texts: list[str] = [self.data[k][0].emb_text for k in keys]
        # Serialize data as JSON strings
        data_strings: list[str] = [
            json.dumps(self.data[k][0].data) if self.data[k][0].data is not None else ""
            for k in keys
        ]
        embeddings = np.array([self.data[k][1] for k in keys])
        np.savez_compressed(
            path,
            keys=keys,
            texts=texts,
            data=data_strings,
            embeddings=embeddings,
        )

    @classmethod
    def read_from_npz(cls, path: Path) -> Embeddings:
        """Load embeddings from numpy's compressed format."""
        import numpy as np

        with np.load(path) as npz_data:
            if "data" in npz_data.files:
                data_array = npz_data["data"]
            else:
                # No data column, so no data.
                data_array = None

            loaded_data: dict[Key, tuple[EmbValue, list[float]]] = {}
            for i, (k, t, e) in enumerate(
                zip(
                    npz_data["keys"],
                    npz_data["texts"],
                    npz_data["embeddings"],
                    strict=False,
                )
            ):
                data_str = data_array[i] if data_array is not None else ""
                loaded_data[k] = (
                    EmbValue(emb_text=t, data=json.loads(data_str) if data_str else None),
                    e.tolist(),
                )

        return cls(data=loaded_data)

    def __str__(self) -> str:
        dims: int = -1 if len(self.data) == 0 else len(next(iter(self.data.values()))[1])
        return f"Embeddings({len(self.data)} items, {dims} dimensions)"
