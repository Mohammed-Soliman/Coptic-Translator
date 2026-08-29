"""
Phase 4: export lemma/POS frequency stats from the treebank.

This is NOT a dictionary - the treebank only has sentence-level English
translations, not word-level glosses, so we cannot responsibly generate
English meanings for these lemmas without a real word-alignment step
(e.g. giza/fast_align over the parallel sentences, or manual annotation).
That's future work - see the TODO in ARCHITECTURE.md.

What this DOES give us: a frequency-ranked list of real, attested Coptic
lemmas with their part of speech, useful for:
  - prioritizing which words to manually gloss first for the lexicon
  - grammar/coverage validation (Phase 7) - "is this a known Coptic word
    at all", independent of whether we know its English meaning

Usage:
    python -m training.preprocessing.export_lemma_frequencies
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from backend.corpus.conllu import Corpus

OUTPUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "corpus"
    / "lemma_frequencies.json"
)


def main() -> None:
    corpus = Corpus.from_directory()
    counts: Counter[tuple[str, str]] = Counter()
    for sentence in corpus.sentences:
        for token in sentence.tokens:
            if token.upos == "PUNCT":
                continue
            counts[(token.lemma, token.upos)] += 1

    ranked = [
        {"lemma": lemma, "upos": upos, "count": count}
        for (lemma, upos), count in counts.most_common()
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(ranked, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(ranked)} unique (lemma, POS) pairs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
