"""
Thin wrapper around the baseline Hugging Face English<->Coptic models.

This is the Phase 1 MVP translation layer described in ARCHITECTURE.md:
just the neural baseline, no retrieval/grammar/validation yet. Those get
layered on in later phases without changing this interface.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

EN2COP_MODEL_NAME = "megalaa/english-coptic-translator"
COP2EN_MODEL_NAME = "megalaa/coptic-english-translator"


class Translator:
    """Lazily loads and runs the baseline translation models."""

    def __init__(self) -> None:
        self._en2cop_pipeline = None
        self._cop2en_pipeline = None

    # -- lazy loading -------------------------------------------------

    def _load_en2cop(self):
        if self._en2cop_pipeline is None:
            from transformers import pipeline

            logger.info("Loading EN->Coptic model: %s", EN2COP_MODEL_NAME)
            self._en2cop_pipeline = pipeline(
                "translation", model=EN2COP_MODEL_NAME
            )
        return self._en2cop_pipeline

    def _load_cop2en(self):
        if self._cop2en_pipeline is None:
            from transformers import pipeline

            logger.info("Loading Coptic->EN model: %s", COP2EN_MODEL_NAME)
            self._cop2en_pipeline = pipeline(
                "translation", model=COP2EN_MODEL_NAME
            )
        return self._cop2en_pipeline

    @property
    def en2cop_loaded(self) -> bool:
        return self._en2cop_pipeline is not None

    @property
    def cop2en_loaded(self) -> bool:
        return self._cop2en_pipeline is not None

    # -- public API -----------------------------------------------------

    def translate_en_to_coptic(self, text: str, dialect: str = "bohairic") -> str:
        """Translate English text to Coptic.

        NOTE: check the model card for `megalaa/english-coptic-translator`
        for the exact way it expects dialect to be specified (e.g. a prefix
        token vs. a separate parameter) and adjust the call below to match.
        """
        translator = self._load_en2cop()
        result = translator(text)
        return result[0]["translation_text"]

    def translate_coptic_to_en(self, text: str, dialect: Optional[str] = None) -> str:
        translator = self._load_cop2en()
        result = translator(text)
        return result[0]["translation_text"]

    def translate(self, text: str, direction: str, dialect: str = "bohairic") -> str:
        if direction == "en2cop":
            return self.translate_en_to_coptic(text, dialect=dialect)
        if direction == "cop2en":
            return self.translate_coptic_to_en(text, dialect=dialect)
        raise ValueError(f"Unknown direction: {direction!r}")


@lru_cache(maxsize=1)
def get_translator() -> Translator:
    """Singleton accessor so the API only builds one Translator instance."""
    return Translator()
