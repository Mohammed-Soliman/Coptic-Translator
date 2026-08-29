"""Basic smoke tests for the FastAPI app.

Note: these will download the HF models on first run of a /translate test,
so they're slow the first time. The health check test doesn't require that.
"""

from dataclasses import dataclass
from fastapi.testclient import TestClient

import backend.api.main as api_main
from backend.corpus.corpus import Corpus, CorpusSentence
from backend.lexicon.lexicon import Lexicon
from backend.retrieval.retriever import RetrievalHit


@dataclass
class FakeTranslationResult:
    text: str
    confidence: float | None = 0.88


class FakeTranslator:
    en2cop_loaded = True
    cop2en_loaded = True

    def translate(self, text: str, direction: str, dialect: str = "bohairic"):
        if direction == "en2cop":
            return FakeTranslationResult(text="ⲡⲟⲩⲣⲟ")
        return FakeTranslationResult(text="the king")


class FakeLexicon:
    def english_coverage(self, text: str) -> float:
        return 0.5


class FakeRetriever:
    def search(self, query: str, top_k: int = 5):
        return [
            RetrievalHit(
                source="corpus",
                title="the king is good",
                text="the king is good",
                score=0.95,
                dialect="bohairic",
                source_ref="unit-test",
                metadata={"coptic": "ⲡⲟⲩⲣⲟ"},
            )
        ]


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(api_main, "get_translator", lambda: FakeTranslator())

    client = TestClient(api_main.app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_en2cop_loaded"] is True
    assert body["model_cop2en_loaded"] is True


def test_translate_endpoint_includes_retrieval_hits(monkeypatch):
    monkeypatch.setattr(api_main, "get_translator", lambda: FakeTranslator())
    monkeypatch.setattr(api_main, "get_retriever", lambda: FakeRetriever())
    monkeypatch.setattr(api_main, "get_lexicon", lambda: FakeLexicon())

    client = TestClient(api_main.app)
    response = client.post(
        "/translate",
        json={"text": "The king is good.", "direction": "en2cop", "dialect": "bohairic"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["output_text"] == "ⲡⲟⲩⲣⲟ"
    assert body["confidence"] == 0.88
    assert body["dictionary_coverage"] == 0.5
    assert len(body["retrieval_hits"]) == 1
    assert body["retrieval_hits"][0]["source"] == "corpus"


def test_retrieve_endpoint(monkeypatch):
    monkeypatch.setattr(api_main, "get_retriever", lambda: FakeRetriever())

    client = TestClient(api_main.app)
    response = client.get("/retrieve", params={"q": "king", "top_k": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["source"] == "corpus"


def test_corpus_search_endpoint(monkeypatch):
    monkeypatch.setattr(
        api_main,
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

    client = TestClient(api_main.app)
    response = client.get("/corpus/search", params={"q": "king", "top_k": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["english"] == "the king is good"
