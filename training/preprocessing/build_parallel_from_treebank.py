"""Build data/parallel/scriptorium_gold.csv from the UD Coptic Scriptorium treebank."""

from __future__ import annotations

import csv
from pathlib import Path

from backend.corpus.conllu import Corpus

OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "parallel" / "scriptorium_gold.csv"
)


def main() -> None:
    corpus = Corpus.from_directory()
    sentences = corpus.translated_sentences
    print(f"Loaded {len(sentences)} translated sentences from the treebank.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "coptic", "dialect", "source", "quality"])
        for s in sentences:
            writer.writerow(
                [
                    s.english_text,
                    s.coptic_text,
                    "sahidic",
                    f"UD_Coptic-Scriptorium/{s.source_file}#{s.sent_id} (CC BY 4.0)",
                    "gold",
                ]
            )

    print(f"Wrote {len(sentences)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
