from backend.grammar.checker import GrammarChecker
from backend.lexicon.lexicon import Lexicon, LexiconEntry


def build_lexicon() -> Lexicon:
    return Lexicon(
        [
            LexiconEntry(
                coptic="ⲡⲟⲩⲣⲟ",
                lemma="ⲡⲟⲩⲣⲟ",
                english=["king"],
                dialect=["bohairic", "sahidic"],
            ),
            LexiconEntry(
                coptic="ⲡⲉ",
                lemma="ⲡⲉ",
                english=["house"],
                dialect=["bohairic"],
            ),
        ]
    )


def test_grammar_checker_accepts_known_coptic_token():
    checker = GrammarChecker(lexicon=build_lexicon())

    result = checker.check("ⲡⲟⲩⲣⲟ", dialect="bohairic")

    assert result.score > 0.0
    assert result.known_token_ratio == 1.0
    assert result.mixed_script is False
    assert not any(issue.rule == "unknown-token" for issue in result.issues)


def test_grammar_checker_flags_mixed_script():
    checker = GrammarChecker(lexicon=build_lexicon())

    result = checker.check("ⲡⲟⲩⲣⲟ king", dialect="bohairic")

    assert result.mixed_script is True
    assert any(issue.rule == "mixed-script" for issue in result.issues)


def test_grammar_checker_flags_unknown_token():
    checker = GrammarChecker(lexicon=build_lexicon())

    result = checker.check("ⲁⲃⲅ", dialect="bohairic")

    assert any(issue.rule == "unknown-token" for issue in result.issues)
    assert result.known_token_ratio == 0.0


def test_grammar_checker_flags_dialect_mismatch():
    checker = GrammarChecker(lexicon=build_lexicon())

    result = checker.check("ⲡⲉ", dialect="sahidic")

    assert any(issue.rule == "dialect-mismatch" for issue in result.issues)
