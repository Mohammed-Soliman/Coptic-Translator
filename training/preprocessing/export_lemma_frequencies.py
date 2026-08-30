"""Export lemma/POS frequency stats from the treebank."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from backend.corpus.conllu import Corpus

OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "corpus" / "lemma_frequencies.json"
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
