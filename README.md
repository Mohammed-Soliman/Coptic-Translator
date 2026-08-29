# Coptic Translator

A hybrid English ↔ Coptic (Bohairic / Sahidic) translation system.

Instead of relying purely on an LLM, this project combines:

- A **baseline neural translation model** (Hugging Face `megalaa/english-coptic-translator`
  and `megalaa/coptic-english-translator`)
- A **structured lexicon and grammar layer**
- **Retrieval-augmented translation** grounded in real Coptic corpora
  (e.g. [Coptic SCRIPTORIUM](https://copticscriptorium.org/))
- An **LLM refinement / validation pass**
- **Confidence scoring** based on dictionary coverage, corpus similarity,
  and grammar validation — not just raw model confidence

See `ARCHITECTURE.md` for the full system design and phased roadmap.

## Status

Baseline translation, the FastAPI backend, structured lexicon (Phase 3),
corpus ingestion (Phase 4), retrieval (Phase 5), grammar checking (Phase 6),
and combined confidence scoring (Phase 7) are all implemented - see
`ARCHITECTURE.md` for how they fit together.

- [x] Repo scaffold
- [x] English → Bohairic / Bohairic → English translation (baseline model)
- [x] FastAPI backend (`backend/api/main.py`)
- [x] Structured lexicon + coverage scoring (Phase 3)
- [x] Corpus ingestion + keyword search (Phase 4)
- [x] Retrieval layer, keyword fallback when FAISS/sentence-transformers
      aren't installed (Phase 5)
- [x] Grammar/surface-form validation (Phase 6)
- [x] Combined confidence scoring (Phase 7) - see `backend/validation/scorer.py`
- [x] Linked web interface - Translator, Lexicon, Manuscripts, and Lab Notes
      pages, styled after Ancient Egyptian/Coptic textile and papyrus art,
      served directly by the FastAPI app (Phase 8, in progress)
- [ ] Fine-tuning on curated parallel data (Phase 6 roadmap item)
- [ ] Real ingested Coptic SCRIPTORIUM corpus (currently just illustrative
      sample sentences - see `data/corpus/README.md`)

A minimal Streamlit prototype (`frontend/app.py`) still exists as a quick
dev sanity-check for the raw `/translate` endpoint, but the linked
interface below is the primary UI now.

## Quickstart

### macOS / Linux

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API - this also serves the web interface
uvicorn backend.api.main:app --reload
```

Then open **http://localhost:8000** - it redirects straight into the
Translator page. Lexicon, Manuscripts, and Lab Notes are reachable from
the sidebar, or directly at `/app/coptic_lexicon.html`,
`/app/manuscripts_gallery.html`, and `/app/lab_notes_metrics.html`.

The old Streamlit prototype still works if you want it, in a second
terminal:

```bash
streamlit run frontend/app.py
```

### Windows (PowerShell)

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it (note: NOT "source" - that's a Mac/Linux command)
.venv\Scripts\Activate.ps1

# If you get an error about execution policy, run this once, then retry:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the API - this also serves the web interface
uvicorn backend.api.main:app --reload
```

> **Tip:** make sure `python` points to a 64-bit install
> (`python -c "import struct;print(struct.calcsize('P')*8)"` should print `64`).
> A 32-bit Python is a common cause of native-dependency build failures on Windows.

Then open **http://localhost:8000** for the linked web interface, or POST to
`http://localhost:8000/translate` directly, e.g.:

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "The teacher went to the house.", "direction": "en2cop", "dialect": "bohairic"}'
```

## Project layout

```
coptic-translator/
├── backend/
│   ├── api/            # FastAPI app + routes; also mounts the frontend
│   ├── translation/     # Wrapper around the HF translation models
│   ├── models/          # Pydantic schemas
│   ├── lexicon/          # Phase 3 structured dictionary + coverage scoring
│   ├── corpus/            # Phase 4 corpus ingestion + keyword search
│   ├── retrieval/          # Phase 5 corpus/lexicon retrieval (keyword fallback)
│   ├── grammar/             # Phase 6 grammar/surface-form validation
│   ├── validation/           # Phase 7 combined confidence scoring
│   └── labnotes/               # JSON-backed store behind the Lab Notes page
├── data/
│   ├── dictionary/       # Lexicon (JSON) - see note below on scraper data
│   ├── parallel/          # Parallel English-Coptic sentence pairs
│   ├── corpus/             # Raw/annotated Coptic corpora (e.g. SCRIPTORIUM exports)
│   ├── evaluation/         # Held-out eval sets + metrics output
│   └── lab_notes.json      # Lab Notes page's persisted entries (auto-created)
├── training/
│   ├── preprocessing/
│   ├── fine_tuning/
│   └── evaluation/
├── frontend/
│   ├── app.py             # Legacy Streamlit dev prototype
│   ├── pages/              # The linked Ancient-Egyptian/Coptic-styled UI
│   │                         (Translator, Lexicon, Manuscripts, Lab Notes)
│   └── assets/js/           # Frontend JS wiring the pages to the API above
├── notebooks/             # Exploration / experiments
├── tests/
├── requirements.txt
├── Dockerfile
└── ARCHITECTURE.md
```

**Note on `data/dictionary/`:** `glosbe_clean.json` was produced by a
scraper that, for many entries, captured whole webpage boilerplate (nav
menus, "Add translation" prompts) instead of a real headword/gloss. The
lexicon loader now filters those out automatically (logged as "skipped
implausible dictionary entries" on startup), so the app only surfaces
`data/dictionary/sample.json`'s 5 clean entries today. Re-scraping Glosbe
with a real HTML parser instead of a raw text dump - or finishing
`crum_clean.json`, which currently has zero entries - would substantially
grow the working lexicon.

## Roadmap (from planning doc)

1. English → Bohairic, Bohairic → English (baseline model) — **current phase**
2. Add Sahidic
3. Add Coptic dictionary layer
4. Ingest Coptic SCRIPTORIUM corpus
5. Add retrieval-augmented generation (RAG)
6. Fine-tune the translation model on curated parallel data
7. Add grammar checker, confidence scoring, alternative translations
8. Polish into a full web application

## Data sources

- [Coptic SCRIPTORIUM](https://copticscriptorium.org/) — corpora, annotations, treebank, NLP tools
- [`megalaa/english-coptic-translator`](https://huggingface.co/megalaa/english-coptic-translator) — baseline EN→Coptic model
- [`megalaa/coptic-english-translator`](https://huggingface.co/megalaa/coptic-english-translator) — baseline Coptic→EN model

## License

Choose a license appropriate for your use (e.g. MIT for code; check licensing
terms separately for any corpus/dictionary data you incorporate, since some
Coptic corpora have their own usage terms).
