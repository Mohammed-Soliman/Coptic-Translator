"""Phase 5 retrieval layer.

This module combines:
- semantic retrieval over corpus + lexicon when sentence-transformers/FAISS are available
- keyword fallback so the API still works in lightweight environments

The retrieval layer is intentionally read-only and side-effect free.
It can be used by translation, validation, or a standalone /retrieve endpoint.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any, Literal, Optional

from backend.corpus.corpus import get_corpus
from backend.lexicon.lexicon import get_lexicon

logger = logging.getLogger(__name__)

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    faiss = None

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    np = None

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None


DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_WORD_RE = re.compile(r"[A-Za-z\u2C80-\u2CFF']+")

SourceType = Literal["corpus", "lexicon"]


@dataclass
class RetrievalHit:
    source: SourceType
    title: str
    text: str
    score: float
    dialect: Optional[str] = None
    source_ref: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _SearchDocument:
    source: SourceType
    title: str
    text: str
    search_text: str
    dialect: Optional[str] = None
    source_ref: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalEngine:
    """Searches structured corpus and lexicon data."""

    def __init__(self, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.embedding_model_name = embedding_model
        self._embedder = None
        self._corpus_docs: list[_SearchDocument] = []
        self._lexicon_docs: list[_SearchDocument] = []
        self._corpus_index = None
        self._lexicon_index = None
        self._corpus_embeddings = None
        self._lexicon_embeddings = None

        self._load_documents()
        self._build_indexes()

    def _load_documents(self) -> None:
        corpus = get_corpus()
        lexicon = get_lexicon()

        self._corpus_docs = [
            _SearchDocument(
                source="corpus",
                title=sentence.english,
                text=sentence.english,
                search_text=f"{sentence.english} {sentence.coptic}",
                dialect=sentence.dialect,
                source_ref=sentence.source,
                metadata={
                    "coptic": sentence.coptic,
                    "english": sentence.english,
                    "tokens": [
                        {
                            "surface": token.surface,
                            "lemma": token.lemma,
                            "pos": token.pos,
                        }
                        for token in sentence.tokens
                    ],
                },
            )
            for sentence in corpus.sentences
        ]

        self._lexicon_docs = [
            _SearchDocument(
                source="lexicon",
                title=entry.lemma,
                text=", ".join(entry.english) if entry.english else entry.lemma,
                search_text=" ".join(
                    [entry.coptic, entry.lemma, *entry.english, *entry.dialect]
                ).strip(),
                dialect=entry.dialect[0] if entry.dialect else None,
                source_ref="dictionary",
                metadata={
                    "coptic": entry.coptic,
                    "lemma": entry.lemma,
                    "english": entry.english,
                    "dialect": entry.dialect,
                    "part_of_speech": entry.part_of_speech,
                    "gender": entry.gender,
                    "sources": entry.sources,
                },
            )
            for entry in lexicon.entries
        ]

        logger.info(
            "Loaded retrieval documents: %d corpus, %d lexicon",
            len(self._corpus_docs),
            len(self._lexicon_docs),
        )

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder

        if SentenceTransformer is None:
            logger.warning(
                "sentence-transformers is not installed; retrieval will use keyword fallback."
            )
            return None

        try:
            self._embedder = SentenceTransformer(self.embedding_model_name)
            return self._embedder
        except Exception:
            logger.exception("Failed to load embedding model: %s", self.embedding_model_name)
            return None

    def _encode(self, texts: list[str]):
        embedder = self._get_embedder()
        if embedder is None or np is None:
            return None

        try:
            vectors = embedder.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vectors.astype("float32")
        except Exception:
            logger.exception("Embedding failed; falling back to keyword retrieval.")
            return None

    def _build_indexes(self) -> None:
        if faiss is None or np is None:
            logger.warning("FAISS or NumPy unavailable; retrieval will use keyword fallback.")
            return

        if self._corpus_docs:
            corpus_vectors = self._encode([doc.search_text for doc in self._corpus_docs])
            if corpus_vectors is not None and len(corpus_vectors) > 0:
                self._corpus_embeddings = corpus_vectors
                self._corpus_index = faiss.IndexFlatIP(corpus_vectors.shape[1])
                self._corpus_index.add(corpus_vectors)

        if self._lexicon_docs:
            lexicon_vectors = self._encode([doc.search_text for doc in self._lexicon_docs])
            if lexicon_vectors is not None and len(lexicon_vectors) > 0:
                self._lexicon_embeddings = lexicon_vectors
                self._lexicon_index = faiss.IndexFlatIP(lexicon_vectors.shape[1])
                self._lexicon_index.add(lexicon_vectors)

        logger.info(
            "Retrieval indexes ready: corpus=%s lexicon=%s",
            self._corpus_index is not None,
            self._lexicon_index is not None,
        )

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        query_words = {w.lower() for w in _WORD_RE.findall(query)}
        if not query_words:
            return 0.0

        text_words = {w.lower() for w in _WORD_RE.findall(text)}
        if not text_words:
            return 0.0

        overlap = len(query_words & text_words)
        return overlap / max(len(query_words), 1)

    @staticmethod
    def _dedupe_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[RetrievalHit] = []

        for hit in hits:
            key = (hit.source, hit.title, hit.text)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(hit)

        return deduped

    def _keyword_search(
        self, query: str, docs: list[_SearchDocument], top_k: int
    ) -> list[RetrievalHit]:
        scored: list[RetrievalHit] = []
        for doc in docs:
            score = self._keyword_score(query, doc.search_text)
            if score <= 0.0:
                continue
            scored.append(
                RetrievalHit(
                    source=doc.source,
                    title=doc.title,
                    text=doc.text,
                    score=score,
                    dialect=doc.dialect,
                    source_ref=doc.source_ref,
                    metadata=doc.metadata,
                )
            )

        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    def _vector_search(
        self,
        query: str,
        docs: list[_SearchDocument],
        index,
        top_k: int,
    ) -> list[RetrievalHit]:
        if index is None or np is None:
            return []

        query_vector = self._encode([query])
        if query_vector is None:
            return []

        k = min(top_k, len(docs))
        if k <= 0:
            return []

        scores, indices = index.search(query_vector, k)
        hits: list[RetrievalHit] = []

        for score, idx in zip(scores[0].tolist(), indices[0].tolist()):
            if idx < 0 or idx >= len(docs):
                continue
            doc = docs[idx]
            hits.append(
                RetrievalHit(
                    source=doc.source,
                    title=doc.title,
                    text=doc.text,
                    score=float(score),
                    dialect=doc.dialect,
                    source_ref=doc.source_ref,
                    metadata=doc.metadata,
                )
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits

    def search(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        query = query.strip()
        if not query:
            return []

        hits: list[RetrievalHit] = []

        if self._corpus_docs:
            if self._corpus_index is not None:
                hits.extend(self._vector_search(query, self._corpus_docs, self._corpus_index, top_k))
            else:
                hits.extend(self._keyword_search(query, self._corpus_docs, top_k))

        if self._lexicon_docs:
            if self._lexicon_index is not None:
                hits.extend(self._vector_search(query, self._lexicon_docs, self._lexicon_index, top_k))
            else:
                hits.extend(self._keyword_search(query, self._lexicon_docs, top_k))

        hits = self._dedupe_hits(hits)
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]

    def context_for(self, query: str, top_k: int = 5) -> dict[str, list[dict[str, Any]]]:
        hits = self.search(query, top_k=top_k)
        return {
            "query": query,
            "hits": [asdict(hit) for hit in hits],
        }


@lru_cache(maxsize=1)
def get_retriever() -> RetrievalEngine:
    """Singleton accessor for application-wide retrieval reuse."""
    return RetrievalEngine()