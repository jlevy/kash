from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kash.concepts.embeddings import Embeddings
from kash.concepts.text_similarity import rank_by_relatedness
from kash.config.logger import get_logger
from kash.help.help_types import HelpDoc, HelpDocType
from kash.web_content.local_file_cache import Loadable

log = get_logger(__name__)


@dataclass(frozen=True)
class DocKey:
    """Unique identifier for a help document in the embeddings."""

    doc_type: HelpDocType
    index: int

    def __str__(self) -> str:
        return f"{self.doc_type.value}:{self.index}"

    @classmethod
    def parse(cls, s: str) -> DocKey:
        doc_type, index = s.split(":")
        return cls(HelpDocType(doc_type), int(index))


@dataclass(frozen=True)
class DocHit:
    doc_key: DocKey
    doc: HelpDoc
    relatedness: float


@dataclass
class HelpIndex:
    docs: list[HelpDoc]
    embeddings: Embeddings = field(init=False)

    def __post_init__(self) -> None:
        self.embeddings = self._embed_and_cache_docs()

    def _docs_by_key(self) -> list[tuple[DocKey, HelpDoc]]:
        return [(DocKey(doc.doc_type, idx), doc) for idx, doc in enumerate(self.docs)]

    def _lookup_doc(self, key: DocKey) -> HelpDoc:
        return self.docs[key.index]

    def _embed_and_cache_docs(self) -> Embeddings:
        """
        Get embeddings for all embeddable help docs, using a cached copy if available.
        """
        from kash.web_content.file_cache_utils import cache_file

        def calculate_and_save_help_embeddings(target_path: Path) -> None:
            keyvals = [(str(key), doc.embedding_text()) for key, doc in self._docs_by_key()]
            embeddings = Embeddings.embed(keyvals)
            log.info("Embedded %d help documents, cached at: %s", len(embeddings.data), target_path)
            embeddings.to_npz(target_path)

        key = f"kash_help_embeddings_v1_{len(self.docs)}.npz"
        path, _ = cache_file(
            Loadable(key, save=calculate_and_save_help_embeddings), global_cache=True
        )
        log.info("Loaded help doc embeddings from: %s", path)
        return Embeddings.read_from_npz(path)

    def rank_docs(self, query: str, max: int = 10, min_cutoff: float = 0.5) -> list[DocHit]:
        ranked_docs = rank_by_relatedness(query, self.embeddings)
        hits = []
        for key_str, _text, relatedness in ranked_docs[:max]:
            if relatedness < min_cutoff:
                break
            key = DocKey.parse(key_str)
            hits.append(DocHit(key, self._lookup_doc(key), relatedness))
        return hits

    def __len__(self) -> int:
        return len(self.docs)

    def __repr__(self) -> str:
        return f"HelpIndex({len(self.docs)} docs)"
