from typing import cast

import litellm
import pandas as pd
from funlog import log_calls, tally_calls
from litellm import embedding
from litellm.types.utils import EmbeddingResponse

from kash.concepts.cosine import cosine
from kash.concepts.embeddings import Embeddings
from kash.config.logger import get_logger
from kash.llm_utils.llms import DEFAULT_EMBEDDING_MODEL, EmbeddingModel
from kash.utils.errors import ApiResultError

log = get_logger(__name__)


def sort_by_length(values: list[str]) -> list[str]:
    return sorted(values, key=lambda x: (len(x), x))


def cosine_relatedness(x, y):
    return 1 - cosine(x, y)


@log_calls(level="info", show_return_value=False)
def embed_query(model: EmbeddingModel, query: str) -> EmbeddingResponse:
    try:
        response: EmbeddingResponse = cast(
            EmbeddingResponse, embedding(model=model.litellm_name, input=[query])
        )
    except litellm.exceptions.APIError as e:
        log.info("API error embedding query: %s", e)
        raise ApiResultError(str(e))
    if not response.data:
        log.info("API error embedding query, got: %s", response)
        raise ApiResultError("No embedding response data")
    return response


@log_calls(level="info", show_return_value=False)
def rank_by_relatedness(
    query: str,
    embeddings: Embeddings,
    relatedness_fn=cosine_relatedness,
    model=DEFAULT_EMBEDDING_MODEL,
    top_n: int = -1,
) -> list[tuple[str, str, float]]:
    """
    Returns a list of strings and relatednesses, sorted from most related to least.
    """
    response = embed_query(model, query)

    query_embedding = response.data[0]["embedding"]

    scored_strings = [
        (key, text, relatedness_fn(query_embedding, emb))
        for key, text, emb in embeddings.as_iterable()
    ]
    scored_strings.sort(key=lambda x: x[2], reverse=True)

    return scored_strings[:top_n]


@tally_calls(level="warning", min_total_runtime=5, if_slower_than=10)
def relate_texts_by_embedding(
    embeddings: Embeddings, relatedness_fn=cosine_relatedness
) -> pd.DataFrame:
    log.message("Computing relatedness matrix of %d text embeddings…", len(embeddings.data))

    keys = [key for key, _, _ in embeddings.as_iterable()]
    relatedness_matrix = pd.DataFrame(index=keys, columns=keys)  # pyright: ignore

    for i, (key1, _, emb1) in enumerate(embeddings.as_iterable()):
        for j, (key2, _, emb2) in enumerate(embeddings.as_iterable()):
            if i <= j:
                score = relatedness_fn(emb1, emb2)
                relatedness_matrix.at[key1, key2] = score
                relatedness_matrix.at[key2, key1] = score

    # Fill diagonal (self-relatedness).
    for key in keys:
        relatedness_matrix.at[key, key] = 1.0

    return relatedness_matrix


def find_related_pairs(
    relatedness_matrix: pd.DataFrame, threshold: float = 0.9
) -> list[tuple[str, str, float]]:
    log.message(
        "Finding near duplicates among %s items (threshold %s)",
        relatedness_matrix.shape[0],
        threshold,
    )

    pairs: list[tuple[str, str, float]] = []
    keys = relatedness_matrix.index.tolist()

    for i, key1 in enumerate(keys):
        for j, key2 in enumerate(keys):
            if i < j:
                relatedness = relatedness_matrix.at[key1, key2]
                if relatedness >= threshold:
                    # Put shortest one first.
                    [short_key, long_key] = sort_by_length([key1, key2])
                    pairs.append((short_key, long_key, relatedness))

    # Sort with highest relatedness first.
    pairs.sort(key=lambda x: x[2], reverse=True)

    return pairs
