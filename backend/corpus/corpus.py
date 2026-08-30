"""Coptic corpus ingestion and keyword search over data/corpus/*.json."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"

_WORD_RE = re.compile(r"[A-Za-z']+")


@dataclass
class CorpusToken:
    surface: str
    lemma: str
    pos: str


@dataclass
class CorpusSentence:
    coptic: str
    english: str
    dialect: str
    source: str
    tokens: list[CorpusToken] = field(default_factory=list)


class Corpus:
    """In-memory annotated sentence corpus loaded from data/corpus/*.json."""

    def __init__(self, sentences: list[CorpusSentence]):
        self.sentences = sentences

    @staticmethod
    def _is_sentence_item(item: object) -> bool:
        return isinstance(item, dict) and "coptic" in item and "english" in item

    @classmethod
    def from_directory(cls, directory: Path = DEFAULT_CORPUS_DIR) -> "Corpus":
        sentences: list[CorpusSentence] = []
        if not directory.exists():
            logger.warning("Corpus directory not found: %s", directory)
            return cls(sentences)

        for path in sorted(directory.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.exception("Failed to parse corpus file: %s", path)
                continue

            if not isinstance(raw, list):
                logger.info("Skipping non-list corpus file: %s", path)
                continue

            sentence_items = [item for item in raw if cls._is_sentence_item(item)]
            if not sentence_items:
                logger.info("Skipping non-sentence corpus file: %s", path)
                continue

            for item in sentence_items:
                try:
                    tokens = [
                        CorpusToken(
                            surface=t["surface"], lemma=t["lemma"], pos=t["pos"]
                        )
                        for t in item.get("tokens", [])
                        if isinstance(t, dict)
                        and "surface" in t
                        and "lemma" in t
                        and "pos" in t
                    ]
                    sentences.append(
                        CorpusSentence(
                            coptic=item["coptic"],
                            english=item["english"],
                            dialect=item.get("dialect", "unknown"),
                            source=item.get("source", "unknown"),
                            tokens=tokens,
                        )
                    )
                except KeyError:
                    logger.warning(
                        "Skipping malformed corpus entry in %s: %r", path, item
                    )

        logger.info("Loaded %d corpus sentences from %s", len(sentences), directory)
        return cls(sentences)

    def search_english(self, query: str, top_k: int = 5) -> list[CorpusSentence]:
        """Naive keyword-overlap search over English glosses."""
        query_words = {w.lower() for w in _WORD_RE.findall(query)}
        if not query_words:
            return []

        scored: list[tuple[int, CorpusSentence]] = []
        for sentence in self.sentences:
            sentence_words = {w.lower() for w in _WORD_RE.findall(sentence.english)}
            overlap = len(query_words & sentence_words)
            if overlap > 0:
                scored.append((overlap, sentence))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [sentence for _, sentence in scored[:top_k]]


@lru_cache(maxsize=1)
def get_corpus() -> Corpus:
    """Singleton accessor, mirroring get_lexicon() / get_translator()."""
    return Corpus.from_directory()
