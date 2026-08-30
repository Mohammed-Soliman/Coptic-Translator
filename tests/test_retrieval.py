from dataclasses import dataclass

import backend.retrieval.retriever as retriever_module
from backend.lexicon.lexicon import Lexicon, LexiconEntry
from backend.corpus.corpus import Corpus, CorpusSentence
from backend.retrieval.retriever import RetrievalEngine


def test_retrieval_engine_keyword_fallback(monkeypatch):
    monkeypatch.setattr(retriever_module, "SentenceTransformer", None)
    monkeypatch.setattr(retriever_module, "faiss", None)
    monkeypatch.setattr(retriever_module, "np", None)

    monkeypatch.setattr(
        retriever_module,
        "get_corpus",
        lambda: Corpus(
            [
                CorpusSentence(
                    coptic="ⲡⲟⲩⲣⲟ",
                    english="the king is good",
                    dialect="bohairic",
                    source="unit-test",
                )
            ]
        ),
    )

    monkeypatch.setattr(
        retriever_module,
        "get_lexicon",
        lambda: Lexicon(
            [
                LexiconEntry(
                    coptic="ⲡⲟⲩⲣⲟ",
                    lemma="ⲡⲟⲩⲣⲟ",
                    english=["king"],
                    dialect=["bohairic"],
                )
            ]
        ),
    )

    engine = RetrievalEngine()
    hits = engine.search("king", top_k=5)

    assert hits
    assert any(hit.source == "corpus" for hit in hits)
    assert any(hit.source == "lexicon" for hit in hits)
    assert all(hit.score > 0 for hit in hits)


def test_retrieval_context_for_returns_serializable_payload(monkeypatch):
    monkeypatch.setattr(retriever_module, "SentenceTransformer", None)
    monkeypatch.setattr(retriever_module, "faiss", None)
    monkeypatch.setattr(retriever_module, "np", None)

    monkeypatch.setattr(
        retriever_module,
        "get_corpus",
        lambda: Corpus(
            [
                CorpusSentence(
                    coptic="ⲡⲟⲩⲣⲟ",
                    english="the king is good",
                    dialect="bohairic",
                    source="unit-test",
                )
            ]
        ),
    )
    monkeypatch.setattr(retriever_module, "get_lexicon", lambda: Lexicon([]))

    engine = RetrievalEngine()
    payload = engine.context_for("king", top_k=3)

    assert payload["query"] == "king"
    assert isinstance(payload["hits"], list)
    assert payload["hits"]
