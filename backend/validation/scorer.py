"""
Phase 7: confidence scoring.

Combines several independent, uncalibrated signals into one transparent
breakdown for a given translation:

- model_confidence     - raw score reported by the baseline HF model
- dictionary_coverage  - Phase 3 lexicon coverage of the English side
- grammar_score        - Phase 6 rule-based grammar/surface-form score
                          for the Coptic side
- retrieval_support    - Phase 5 signal for how much relevant corpus/
                          lexicon context we found to ground the translation

Per ARCHITECTURE.md: never present a single number as a calibrated
probability. This module is a documented, fixed-weight heuristic - each
component stays visible in the breakdown so the UI can show *why* a score
is low (e.g. "no dictionary coverage" vs. "grammar issues") instead of
collapsing everything into one opaque figure. Any component that isn't
available for a given request (e.g. grammar_score when there's no Coptic
text yet) is simply left out of the weighted average rather than being
treated as zero.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Optional

from backend.grammar.checker import get_grammar_checker
from backend.lexicon.lexicon import get_lexicon
from backend.retrieval.retriever import get_retriever

# Fixed weights, not learned/calibrated - see module docstring.
_WEIGHTS: dict[str, float] = {
    "model_confidence": 0.40,
    "dictionary_coverage": 0.25,
    "grammar_score": 0.25,
    "retrieval_support": 0.10,
}

# Labels are coarse buckets for display, not precise probability bands.
_LABEL_THRESHOLDS = [
    (0.80, "High"),
    (0.55, "Moderate"),
    (0.30, "Low"),
]


def _label_for(score: float) -> str:
    for threshold, label in _LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Very Low"


@dataclass
class ConfidenceBreakdown:
    overall: float
    label: str
    model_confidence: Optional[float]
    dictionary_coverage: Optional[float]
    grammar_score: Optional[float]
    retrieval_support: Optional[float]
    weights: dict[str, float] = field(default_factory=lambda: dict(_WEIGHTS))

    def to_dict(self) -> dict:
        return asdict(self)


class ConfidenceScorer:
    """Combines Phase 3/5/6 signals with raw model confidence."""

    def __init__(self) -> None:
        self.lexicon = get_lexicon()
        self.grammar_checker = get_grammar_checker()
        self.retriever = get_retriever()

    def score(
        self,
        *,
        query_text: str,
        english_text: str,
        coptic_text: str,
        dialect: str = "bohairic",
        model_confidence: Optional[float] = None,
    ) -> ConfidenceBreakdown:
        dictionary_coverage: Optional[float] = None
        if english_text.strip():
            dictionary_coverage = self.lexicon.english_coverage(english_text)

        grammar_score: Optional[float] = None
        if coptic_text.strip():
            grammar_score = self.grammar_checker.check(
                coptic_text, dialect=dialect
            ).score

        retrieval_support: Optional[float] = None
        if query_text.strip():
            hits = self.retriever.search(query_text, top_k=5)
            # Normalize hit count into 0-1: 5+ relevant hits = full support.
            retrieval_support = min(1.0, len(hits) / 5) if hits else 0.0

        components = {
            "model_confidence": model_confidence,
            "dictionary_coverage": dictionary_coverage,
            "grammar_score": grammar_score,
            "retrieval_support": retrieval_support,
        }

        weighted_sum = 0.0
        used_weight = 0.0
        for key, value in components.items():
            if value is None:
                continue
            weight = _WEIGHTS[key]
            weighted_sum += value * weight
            used_weight += weight

        overall = (weighted_sum / used_weight) if used_weight > 0 else 0.0
        overall = max(0.0, min(1.0, overall))

        return ConfidenceBreakdown(
            overall=round(overall, 4),
            label=_label_for(overall),
            model_confidence=(
                round(model_confidence, 4) if model_confidence is not None else None
            ),
            dictionary_coverage=(
                round(dictionary_coverage, 4)
                if dictionary_coverage is not None
                else None
            ),
            grammar_score=(
                round(grammar_score, 4) if grammar_score is not None else None
            ),
            retrieval_support=(
                round(retrieval_support, 4) if retrieval_support is not None else None
            ),
        )


@lru_cache(maxsize=1)
def get_confidence_scorer() -> ConfidenceScorer:
    """Singleton accessor, mirroring the other get_*() functions."""
    return ConfidenceScorer()
