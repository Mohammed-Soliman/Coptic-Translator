"""Persistent JSON-backed log of model/corpus/grammar/eval notes for the Lab Notes page."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_NOTES_PATH = Path(__file__).resolve().parents[2] / "data" / "lab_notes.json"

CATEGORIES = ["Model", "Corpus", "Grammar", "Eval"]

_SEED_NOTES: list[dict] = [
    {
        "id": 1,
        "date": "2024-10-08",
        "category": "Grammar",
        "title": "Jussive vs. optative ambiguity",
        "content": (
            "The rule-based checker can't yet differentiate jussive and "
            "optative moods in fragmentary clauses lacking an explicit "
            "modal base. Considering a dependency heuristic keyed on "
            "preceding verbal valency."
        ),
        "metric_label": "Parse accuracy (target)",
        "metric_value": 0.885,
    },
    {
        "id": 2,
        "date": "2024-10-12",
        "category": "Corpus",
        "title": "Scriptorium alignment gaps",
        "content": (
            "Several ingested sentences have orthographic variants the "
            "naive keyword search treats as noise. Needs lexicon overrides "
            "for known scribal spelling variation before Phase 5 retrieval "
            "quality can be trusted."
        ),
        "metric_label": "Alignment integrity",
        "metric_value": 0.428,
    },
    {
        "id": 3,
        "date": "2024-10-14",
        "category": "Model",
        "title": "Baseline model confidence on short inputs",
        "content": (
            "Short single-word inputs to the baseline EN->Coptic model "
            "report unusually high confidence relative to longer sentences. "
            "Worth weighting model_confidence down for inputs under ~3 "
            "tokens in the validation layer."
        ),
        "metric_label": "Short-input confidence (observed)",
        "metric_value": 0.642,
    },
]


@dataclass
class LabNote:
    id: int
    date: str
    category: str
    title: str
    content: str
    metric_label: Optional[str] = None
    metric_value: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


class LabNotesStore:
    """Thread-safe, file-backed list of lab notes."""

    def __init__(self, path: Path = DEFAULT_NOTES_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._notes: list[LabNote] = self._load()

    def _load(self) -> list[LabNote]:
        if not self.path.exists():
            self._write(_SEED_NOTES)
            return [LabNote(**item) for item in _SEED_NOTES]
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [LabNote(**item) for item in raw]
        except Exception:
            logger.exception("Failed to load lab notes from %s", self.path)
            return []

    def _write(self, notes: list) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = [n if isinstance(n, dict) else n.to_dict() for n in notes]
        self.path.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def list(self, category: Optional[str] = None) -> list[dict]:
        notes = self._notes
        if category and category.lower() != "all":
            notes = [n for n in notes if n.category.lower() == category.lower()]
        return [n.to_dict() for n in sorted(notes, key=lambda n: n.id, reverse=True)]

    def add(
        self,
        *,
        title: str,
        category: str,
        content: str,
        metric_label: Optional[str] = None,
        metric_value: Optional[float] = None,
    ) -> dict:
        category = category if category in CATEGORIES else "Model"
        with self._lock:
            next_id = max((n.id for n in self._notes), default=0) + 1
            note = LabNote(
                id=next_id,
                date=date.today().isoformat(),
                category=category,
                title=title.strip(),
                content=content.strip(),
                metric_label=metric_label,
                metric_value=metric_value,
            )
            self._notes.append(note)
            self._write(self._notes)
            return note.to_dict()


@lru_cache(maxsize=1)
def get_notes_store() -> LabNotesStore:
    """Singleton accessor, mirroring get_lexicon() / get_corpus()."""
    return LabNotesStore()
