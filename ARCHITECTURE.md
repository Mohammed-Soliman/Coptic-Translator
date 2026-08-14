# Architecture

## Guiding principle

**Translation Model + Coptic Linguistic Resources + Retrieval + Validation + LLM**

rather than simply **LLM → Coptic**.

Coptic is a low-resource language, so a single end-to-end LLM call is unreliable.
This system treats the neural translation model as one component among several,
grounded by structured lexicon data, real corpora, and validation rules.

## Pipeline (target state)

```
User input
    |
Language detection
    |
Dialect detection (Bohairic / Sahidic)
    |
Normalization
    |
Morphological / linguistic analysis
    |
Retrieval (dictionary + corpus)
    |
Translation model
    |
LLM refinement
    |
Grammar / terminology validation
    |
Final translation + confidence score
```

## Components

- **backend/translation** — wraps the baseline Hugging Face models
  (`megalaa/english-coptic-translator`, `megalaa/coptic-english-translator`).
- **backend/retrieval** — (Phase 5) embeds and retrieves similar sentences
  from `data/corpus` and relevant entries from `data/dictionary` to ground
  the translation model / LLM refinement step.
- **backend/grammar** — (Phase 7) rule-based validation: character set,
  tokenization, known vocabulary, agreement, article usage, dialect
  consistency.
- **backend/validation** — (Phase 7) confidence scoring combining model
  confidence, dictionary coverage, corpus similarity, and grammar validation
  results. Never present a single number as a calibrated probability without
  an actual evaluation behind it.

## Data model (target)

```
coptic_words
  id, surface_form, lemma, dialect, pos, english_meaning, morphology, source, confidence

sentences
  id, coptic, english, dialect, source, quality (gold/silver/bronze), verified

grammar_rules
  id, dialect, category, pattern, explanation

translation_history
  id, input, output, dialect, model, confidence, timestamp
```

For the MVP these can just be JSON/CSV files under `data/`; move to
PostgreSQL once the schema stabilizes (see `requirements.txt` for optional
`psycopg2`/`sqlalchemy`).

## Evaluation

Don't rely on BLEU alone. Track, per model version:

- BLEU, chrF, COMET, TER
- Human evaluation
- Coptic-specific: lexical accuracy, morphological accuracy, dialect
  accuracy, grammar accuracy, terminology accuracy

Compare: baseline model → fine-tuned → fine-tuned + RAG → fine-tuned + RAG +
validation, to show the value each layer adds.

## Phases

1. English ↔ Bohairic MVP using the baseline HF models (this scaffold)
2. Add Sahidic dialect support
3. Structured dictionary (`data/dictionary`)
4. Ingest Coptic SCRIPTORIUM corpus (`data/corpus`)
5. Retrieval-augmented translation (`backend/retrieval`)
6. Fine-tune the translation model on curated parallel data (`training/`)
7. Grammar validator + confidence scoring + alternative translations
8. Polished web application (React/Next.js frontend, Docker deployment)
