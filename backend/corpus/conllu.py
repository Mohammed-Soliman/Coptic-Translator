"""Parses the UD Coptic Scriptorium treebank (CoNLL-U format) into in-memory sentences."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CORPUS_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "corpus" / "ud_coptic_scriptorium"
)


@dataclass
class Token:
    id: str
    form: str
    lemma: str
    upos: str
    xpos: str
    feats: str
    misc: str


@dataclass
class CorpusSentence:
    sent_id: str
    coptic_text: str
    english_text: Optional[str]
    tokens: list[Token] = field(default_factory=list)
    source_file: str = ""


def parse_conllu_file(path: Path) -> list[CorpusSentence]:
    """Parse one CoNLL-U file into a list of CorpusSentence."""
    sentences: list[CorpusSentence] = []

    sent_id: Optional[str] = None
    coptic_text: Optional[str] = None
    english_text: Optional[str] = None
    tokens: list[Token] = []

    def flush():
        if coptic_text is not None:
            sentences.append(
                CorpusSentence(
                    sent_id=sent_id or "",
                    coptic_text=coptic_text,
                    english_text=english_text,
                    tokens=list(tokens),
                    source_file=path.name,
                )
            )

    with path.open(encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            if not line.strip():
                flush()
                sent_id, coptic_text, english_text, tokens = None, None, None, []
                continue

            if line.startswith("#"):
                if line.startswith("# sent_id ="):
                    sent_id = line.split("=", 1)[1].strip()
                elif line.startswith("# text ="):
                    coptic_text = line.split("=", 1)[1].strip()
                elif line.startswith("# text_en ="):
                    english_text = line.split("=", 1)[1].strip()
                continue

            fields = line.split("\t")
            if len(fields) != 10:
                continue
            token_id = fields[0]
            if "-" in token_id or "." in token_id:
                continue
            tok = Token(
                id=token_id,
                form=fields[1],
                lemma=fields[2],
                upos=fields[3],
                xpos=fields[4],
                feats=fields[5],
                misc=fields[9],
            )
            tokens.append(tok)

    flush()
    return sentences


class Corpus:
    """All loaded treebank sentences, with a couple of simple lookups."""

    def __init__(self, sentences: list[CorpusSentence]):
        self.sentences = sentences

    @classmethod
    def from_directory(cls, directory: Path = DEFAULT_CORPUS_DIR) -> "Corpus":
        sentences: list[CorpusSentence] = []
        if not directory.exists():
            logger.warning("Corpus directory not found: %s", directory)
            return cls(sentences)

        for path in sorted(directory.glob("*.conllu")):
            try:
                sentences.extend(parse_conllu_file(path))
            except Exception:
                logger.exception("Failed to parse corpus file: %s", path)

        logger.info("Loaded %d corpus sentences from %s", len(sentences), directory)
        return cls(sentences)

    @property
    def translated_sentences(self) -> list[CorpusSentence]:
        """Only sentences that have an English translation."""
        return [s for s in self.sentences if s.english_text]

    def stats(self) -> dict:
        total = len(self.sentences)
        translated = len(self.translated_sentences)
        total_tokens = sum(len(s.tokens) for s in self.sentences)
        return {
            "sentences": total,
            "sentences_with_english": translated,
            "tokens": total_tokens,
        }
