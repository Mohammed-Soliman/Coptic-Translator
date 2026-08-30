import json

from backend.corpus.corpus import Corpus, CorpusSentence


def test_corpus_loader_ignores_auxiliary_json_files(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    (corpus_dir / "sentences.json").write_text(
        json.dumps(
            [
                {
                    "coptic": "ⲡⲟⲩⲣⲟ",
                    "english": "the king",
                    "dialect": "bohairic",
                    "source": "unit-test",
                    "tokens": [
                        {"surface": "the", "lemma": "the", "pos": "DET"},
                        {"surface": "king", "lemma": "king", "pos": "NOUN"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    (corpus_dir / "lemma_frequencies.json").write_text(
        json.dumps(
            [
                {"lemma": "ⲡⲟⲩⲣⲟ", "upos": "NOUN", "count": 1},
                {"lemma": "ⲡⲁⲣⲁ", "upos": "ADP", "count": 1},
            ]
        ),
        encoding="utf-8",
    )

    corpus = Corpus.from_directory(corpus_dir)

    assert len(corpus.sentences) == 1
    assert corpus.sentences[0].english == "the king"
    assert corpus.sentences[0].coptic == "ⲡⲟⲩⲣⲟ"


def test_corpus_keyword_search_returns_matching_sentence():
    corpus = Corpus(
        [
            CorpusSentence(
                coptic="ⲡⲟⲩⲣⲟ",
                english="the king is good",
                dialect="bohairic",
                source="unit-test",
            ),
            CorpusSentence(
                coptic="ⲡⲉ",
                english="the house is large",
                dialect="bohairic",
                source="unit-test",
            ),
        ]
    )

    results = corpus.search_english("king good", top_k=5)

    assert len(results) == 1
    assert results[0].english == "the king is good"
