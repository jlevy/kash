from typing import cast

import litellm
from funlog import log_calls
from litellm import embedding
from litellm.types.utils import EmbeddingResponse

from kash.concepts.cosine import ArrayLike, cosine
from kash.concepts.embeddings import Embeddings
from kash.config.logger import get_logger
from kash.llm_utils.llms import DEFAULT_EMBEDDING_MODEL, EmbeddingModel
from kash.utils.errors import ApiResultError

log = get_logger(__name__)


def cosine_relatedness(x: ArrayLike, y: ArrayLike) -> float:
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
