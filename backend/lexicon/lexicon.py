"""Structured Coptic lexicon: entry lookup and English-coverage scoring."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DICTIONARY_DIR = Path(__file__).resolve().parents[2] / "data" / "dictionary"

_WORD_RE = re.compile(r"[A-Za-z']+")


@dataclass
class LexiconEntry:
    coptic: str
    lemma: str
    english: list[str]
    dialect: list[str]
    part_of_speech: Optional[str] = None
    gender: Optional[str] = None
    sources: Optional[list[str]] = None


class Lexicon:
    """In-memory dictionary loaded from data/dictionary/*.json."""

    def __init__(self, entries: list[LexiconEntry]):
        self.entries = entries
        self._english_index: dict[str, list[LexiconEntry]] = {}
        self._coptic_index: dict[str, list[LexiconEntry]] = {}

        for entry in entries:
            for word in entry.english:
                self._english_index.setdefault(word.lower(), []).append(entry)
            self._coptic_index.setdefault(entry.coptic.casefold(), []).append(entry)

    @staticmethod
    def _normalize_sources(raw_sources) -> Optional[list[str]]:
        """Normalize `sources` (string or attribution-object list) to list[str]."""
        if not raw_sources:
            return None
        normalized: list[str] = []
        for item in raw_sources:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("source") or "source"
                url = item.get("url")
                normalized.append(f"{name} ({url})" if url else str(name))
            else:
                normalized.append(str(item))
        return normalized

    _MAX_COPTIC_ENTRY_LENGTH = 40
    _MAX_ENGLISH_GLOSS_LENGTH = 60
    _COPTIC_RANGE_RE = re.compile(r"[\u2C80-\u2CFF]")
    _BOILERPLATE_MARKERS = (
        "glosbe",
        "@media",
        "add translation",
        "add example",
        "translation memory",
        "privacy policy",
        "terms of service",
    )

    @classmethod
    def _is_plausible_entry(cls, coptic: str) -> bool:
        if not coptic or len(coptic) > cls._MAX_COPTIC_ENTRY_LENGTH:
            return False
        return bool(cls._COPTIC_RANGE_RE.search(coptic))

    @classmethod
    def _clean_english_glosses(cls, raw_english: list) -> list[str]:
        cleaned: list[str] = []
        for gloss in raw_english or []:
            if not isinstance(gloss, str):
                continue
            gloss = gloss.strip()
            if not gloss or len(gloss) > cls._MAX_ENGLISH_GLOSS_LENGTH:
                continue
            lowered = gloss.lower()
            if any(marker in lowered for marker in cls._BOILERPLATE_MARKERS):
                continue
            cleaned.append(gloss)
        return cleaned

    @classmethod
    def from_directory(cls, directory: Path = DEFAULT_DICTIONARY_DIR) -> "Lexicon":
        entries: list[LexiconEntry] = []
        skipped = 0
        if not directory.exists():
            logger.warning("Dictionary directory not found: %s", directory)
            return cls(entries)

        for path in sorted(directory.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.exception("Failed to parse dictionary file: %s", path)
                continue

            if isinstance(raw, dict):
                items = raw.get("entries", [])
            elif isinstance(raw, list):
                items = raw
            else:
                logger.info("Skipping unrecognized dictionary file shape: %s", path)
                continue

            for item in items:
                if not isinstance(item, dict) or "coptic" not in item:
                    logger.warning(
                        "Skipping malformed dictionary entry in %s: %r", path, item
                    )
                    continue
                cleaned_english = cls._clean_english_glosses(item.get("english", []))
                if not cls._is_plausible_entry(item["coptic"]) or not cleaned_english:
                    skipped += 1
                    continue
                lemma = item.get("lemma") or item["coptic"]
                if (
                    not isinstance(lemma, str)
                    or len(lemma) > cls._MAX_COPTIC_ENTRY_LENGTH
                ):
                    lemma = item["coptic"]

                entries.append(
                    LexiconEntry(
                        coptic=item["coptic"],
                        lemma=lemma,
                        english=cleaned_english,
                        dialect=item.get("dialect", []),
                        part_of_speech=item.get("part_of_speech"),
                        gender=item.get("gender"),
                        sources=cls._normalize_sources(item.get("sources")),
                    )
                )

        if skipped:
            logger.warning(
                "Skipped %d implausible dictionary entries (likely scraper artifacts)",
                skipped,
            )
        logger.info("Loaded %d lexicon entries from %s", len(entries), directory)
        return cls(entries)

    def lookup_english(self, word: str) -> list[LexiconEntry]:
        return self._english_index.get(word.lower(), [])

    def lookup_coptic(self, word: str) -> list[LexiconEntry]:
        return self._coptic_index.get(word.casefold(), [])

    def english_coverage(self, text: str) -> float:
        """Fraction (0-1) of English content words in `text` found in the lexicon."""
        words = _WORD_RE.findall(text)
        if not words:
            return 0.0
        known = sum(1 for w in words if self.lookup_english(w))
        return known / len(words)


@lru_cache(maxsize=1)
def get_lexicon() -> Lexicon:
    """Singleton accessor, mirroring get_translator() in translation/translator.py."""
    return Lexicon.from_directory()
