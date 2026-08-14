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

## Status: Phase 1 (MVP)

- [x] Repo scaffold
- [ ] English → Bohairic translation (baseline model)
- [ ] Bohairic → English translation (baseline model)
- [ ] Minimal FastAPI backend
- [ ] Minimal Streamlit frontend

## Quickstart

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API
uvicorn backend.api.main:app --reload

# 4. In another terminal, run the frontend
streamlit run frontend/app.py
```

Then open http://localhost:8501 for the UI, or POST to
`http://localhost:8000/translate` directly, e.g.:

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "The Lord is my shepherd.", "direction": "en2cop", "dialect": "bohairic"}'
```

## Project layout

```
coptic-translator/
├── backend/
│   ├── api/            # FastAPI app + routes
│   ├── translation/     # Wrapper around the HF translation models
│   ├── models/          # Pydantic schemas
│   ├── retrieval/        # (Phase 5) RAG over corpus + dictionary
│   ├── grammar/           # (Phase 7) grammar validation rules
│   └── validation/        # (Phase 7) confidence scoring
├── data/
│   ├── dictionary/       # Lexicon (JSON/CSV)
│   ├── parallel/          # Parallel English-Coptic sentence pairs
│   ├── corpus/             # Raw/annotated Coptic corpora (e.g. SCRIPTORIUM exports)
│   └── evaluation/         # Held-out eval sets + metrics output
├── training/
│   ├── preprocessing/
│   ├── fine_tuning/
│   └── evaluation/
├── frontend/              # Streamlit prototype UI
├── notebooks/             # Exploration / experiments
├── tests/
├── requirements.txt
├── Dockerfile
└── ARCHITECTURE.md
```

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
