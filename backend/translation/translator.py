"""Wrapper around the baseline Hugging Face English<->Coptic translation models."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

EN2COP_MODEL_NAME = "megalaa/english-coptic-translator"
COP2EN_MODEL_NAME = "megalaa/coptic-english-translator"

EN2COP_MODEL_REVISION = "c1cae17da007165feeb3699d3c7a11bcb2aa9665"


@dataclass
class TranslationResult:
    text: str
    confidence: Optional[float] = None


class Translator:
    """Lazily loads and runs the baseline translation models."""

    def __init__(self) -> None:
        self._en2cop_pipeline = None
        self._cop2en_pipeline = None

    def _load_en2cop(self):
        if self._en2cop_pipeline is None:
            from transformers import pipeline

            logger.info(
                "Loading EN->Coptic model: %s (revision %s)",
                EN2COP_MODEL_NAME,
                EN2COP_MODEL_REVISION,
            )
            self._en2cop_pipeline = pipeline(
                model=EN2COP_MODEL_NAME,
                revision=EN2COP_MODEL_REVISION,
                trust_remote_code=True,
            )
        return self._en2cop_pipeline

    def _load_cop2en(self):
        if self._cop2en_pipeline is None:
            from transformers import pipeline

            logger.info("Loading Coptic->EN model: %s", COP2EN_MODEL_NAME)
            self._cop2en_pipeline = pipeline(
                model=COP2EN_MODEL_NAME, trust_remote_code=True
            )
        return self._cop2en_pipeline

    @property
    def en2cop_loaded(self) -> bool:
        return self._en2cop_pipeline is not None

    @property
    def cop2en_loaded(self) -> bool:
        return self._cop2en_pipeline is not None

    @staticmethod
    def _parse_output(result) -> TranslationResult:
        """Handle both the custom-handler dict output and the generic HF pipeline list output."""
        if isinstance(result, dict):
            text = result.get("translation") or result.get("translation_text") or ""
            confidence = result.get("confidence")
            return TranslationResult(text=text, confidence=confidence)
        if isinstance(result, list) and result:
            first = result[0]
            text = first.get("translation") or first.get("translation_text") or ""
            confidence = first.get("confidence")
            return TranslationResult(text=text, confidence=confidence)
        raise ValueError(f"Unexpected pipeline output shape: {result!r}")

    def translate_en_to_coptic(
        self, text: str, dialect: str = "bohairic"
    ) -> TranslationResult:
        translator = self._load_en2cop()
        result = translator(
            text, to_bohairic=(dialect == "bohairic"), output_confidence=True
        )
        return self._parse_output(result)

    def translate_coptic_to_en(
        self, text: str, dialect: Optional[str] = None
    ) -> TranslationResult:
        translator = self._load_cop2en()
        try:
            result = translator(text, output_confidence=True)
        except TypeError:
            result = translator(text)
        return self._parse_output(result)

    def translate(
        self, text: str, direction: str, dialect: str = "bohairic"
    ) -> TranslationResult:
        if direction == "en2cop":
            return self.translate_en_to_coptic(text, dialect=dialect)
        if direction == "cop2en":
            return self.translate_coptic_to_en(text, dialect=dialect)
        raise ValueError(f"Unknown direction: {direction!r}")


@lru_cache(maxsize=1)
def get_translator() -> Translator:
    """Singleton accessor so the API only builds one Translator instance."""
    return Translator()
