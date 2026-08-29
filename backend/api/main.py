"""FastAPI backend for the Coptic translator.

Also serves the linked Ancient-Egyptian/Coptic-styled web frontend
(frontend/pages/*.html + frontend/assets/) as static files, so the whole
app runs from a single `uvicorn backend.api.main:app` process with no
separate dev server or CORS setup required.
"""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.corpus.corpus import get_corpus
from backend.grammar.checker import get_grammar_checker
from backend.labnotes.notes import get_notes_store
from backend.lexicon.lexicon import get_lexicon
from backend.models.schemas import (
    ConfidenceBreakdown,
    GrammarCheckResponse,
    HealthResponse,
    LabNote,
    LabNoteCreate,
    LexiconEntryResponse,
    ManuscriptSummary,
    RetrievalHit,
    TranslationRequest,
    TranslationResponse,
)
from backend.retrieval.retriever import get_retriever
from backend.translation.translator import (
    COP2EN_MODEL_NAME,
    EN2COP_MODEL_NAME,
    get_translator,
)
from backend.validation.scorer import get_confidence_scorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title="Coptic Translator API",
    description="English <-> Coptic (Bohairic / Sahidic) translation service.",
    version="0.2.0",
)

# Loosen for local dev; tighten before deploying publicly. Since the
# frontend is now served from this same app, cross-origin requests are
# only relevant for the Streamlit dev prototype and direct API use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    translator = get_translator()
    return HealthResponse(
        status="ok",
        model_en2cop_loaded=translator.en2cop_loaded,
        model_cop2en_loaded=translator.cop2en_loaded,
    )


@app.post("/translate", response_model=TranslationResponse)
def translate(request: TranslationRequest) -> TranslationResponse:
    translator = get_translator()
    retriever = get_retriever()
    scorer = get_confidence_scorer()

    try:
        result = translator.translate(
            text=request.text,
            direction=request.direction,
            dialect=request.dialect,
        )
    except Exception as exc:  # noqa: BLE001 - surface as a clean 500 for now
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    model_used = EN2COP_MODEL_NAME if request.direction == "en2cop" else COP2EN_MODEL_NAME

    # Phase 3: dictionary coverage is only meaningful over the English side
    # of the exchange (input for en2cop, output for cop2en).
    english_text = request.text if request.direction == "en2cop" else result.text
    coptic_text = result.text if request.direction == "en2cop" else request.text
    coverage = get_lexicon().english_coverage(english_text)

    retrieval_hits = [
        RetrievalHit(**asdict(hit))
        for hit in retriever.search(request.text, top_k=5)
    ]

    # Phase 7: combine model confidence with the lexicon/grammar/retrieval
    # signals above into one transparent breakdown for the UI.
    breakdown = scorer.score(
        query_text=request.text,
        english_text=english_text,
        coptic_text=coptic_text,
        dialect=request.dialect,
        model_confidence=result.confidence,
    )

    return TranslationResponse(
        input_text=request.text,
        output_text=result.text,
        direction=request.direction,
        dialect=request.dialect,
        confidence=result.confidence,
        dictionary_coverage=coverage,
        retrieval_hits=retrieval_hits,
        model=model_used,
        validation=ConfidenceBreakdown(**breakdown.to_dict()),
    )


@app.get("/retrieve")
def retrieve(q: str, top_k: int = 5) -> list[dict]:
    """Phase 5 semantic retrieval over corpus + lexicon."""
    retriever = get_retriever()
    return [asdict(hit) for hit in retriever.search(q, top_k=top_k)]


@app.get("/grammar/check", response_model=GrammarCheckResponse)
def grammar_check(q: str, dialect: str = "bohairic") -> GrammarCheckResponse:
    checker = get_grammar_checker()
    return GrammarCheckResponse(**checker.check(q, dialect=dialect).to_dict())


@app.get("/corpus/search")
def corpus_search(q: str, top_k: int = 5) -> list[dict]:
    """Phase 4: naive keyword search over the ingested corpus.

    Example: GET /corpus/search?q=Jesus%20Christ
    """
    corpus = get_corpus()
    results = corpus.search_english(q, top_k=top_k)
    return [
        {
            "coptic": s.coptic,
            "english": s.english,
            "dialect": s.dialect,
            "source": s.source,
            "tokens": [
                {"surface": t.surface, "lemma": t.lemma, "pos": t.pos} for t in s.tokens
            ],
        }
        for s in results
    ]


@app.get("/corpus/list", response_model=list[ManuscriptSummary])
def corpus_list() -> list[ManuscriptSummary]:
    """Powers the Manuscripts page: one summary card per ingested source."""
    corpus = get_corpus()
    grouped: dict[str, dict] = {}

    for sentence in corpus.sentences:
        entry = grouped.setdefault(
            sentence.source,
            {
                "source": sentence.source,
                "dialect_counts": {},
                "count": 0,
                "annotated": False,
                "sample_coptic": sentence.coptic,
                "sample_english": sentence.english,
            },
        )
        entry["count"] += 1
        entry["dialect_counts"][sentence.dialect] = (
            entry["dialect_counts"].get(sentence.dialect, 0) + 1
        )
        if sentence.tokens:
            entry["annotated"] = True

    summaries = []
    for entry in grouped.values():
        dialect_counts = entry["dialect_counts"]
        dialect = (
            max(dialect_counts, key=dialect_counts.get) if dialect_counts else "unknown"
        )
        summaries.append(
            ManuscriptSummary(
                source=entry["source"],
                dialect=dialect,
                sentence_count=entry["count"],
                annotated=entry["annotated"],
                sample_coptic=entry["sample_coptic"],
                sample_english=entry["sample_english"],
            )
        )

    summaries.sort(key=lambda m: m.sentence_count, reverse=True)
    return summaries


@app.get("/lexicon/search", response_model=list[LexiconEntryResponse])
def lexicon_search(
    q: str = "", dialect: str = "all", pos: str = "any", limit: int = 30
) -> list[LexiconEntryResponse]:
    """Powers the Lexicon page's search + filter toolbar."""
    lexicon = get_lexicon()
    query = q.strip().lower()
    dialect = (dialect or "all").strip().lower()
    pos = (pos or "any").strip().lower()

    results: list[LexiconEntryResponse] = []
    for entry in lexicon.entries:
        if query:
            haystack = " ".join([entry.coptic, entry.lemma, *entry.english]).lower()
            if query not in haystack:
                continue
        if dialect not in ("all", ""):
            if dialect not in [d.lower() for d in entry.dialect]:
                continue
        if pos not in ("any", ""):
            if not entry.part_of_speech or pos not in entry.part_of_speech.lower():
                continue

        results.append(
            LexiconEntryResponse(
                coptic=entry.coptic,
                lemma=entry.lemma,
                english=entry.english,
                dialect=entry.dialect,
                part_of_speech=entry.part_of_speech,
                gender=entry.gender,
                sources=entry.sources,
            )
        )
        if len(results) >= limit:
            break

    return results


@app.get("/lab-notes", response_model=list[LabNote])
def list_lab_notes(category: Optional[str] = None) -> list[LabNote]:
    store = get_notes_store()
    return [LabNote(**note) for note in store.list(category=category)]


@app.post("/lab-notes", response_model=LabNote)
def create_lab_note(note: LabNoteCreate) -> LabNote:
    store = get_notes_store()
    created = store.add(
        title=note.title,
        category=note.category,
        content=note.content,
        metric_label=note.metric_label,
        metric_value=note.metric_value,
    )
    return LabNote(**created)


# --- Frontend static hosting -------------------------------------------
# Mounted last so it never shadows the API routes above.
if (FRONTEND_DIR / "assets").exists():
    app.mount(
        "/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets"
    )
if (FRONTEND_DIR / "pages").exists():
    app.mount(
        "/app", StaticFiles(directory=FRONTEND_DIR / "pages", html=True), name="app"
    )


@app.get("/")
def root() -> RedirectResponse:
    """Land on the Translator page by default."""
    return RedirectResponse(url="/app/coptic_translator.html")
