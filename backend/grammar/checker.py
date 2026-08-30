"""Rule-based grammar and surface-form validation for Coptic text."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Optional

from backend.lexicon.lexicon import Lexicon, get_lexicon

logger = logging.getLogger(__name__)

_COPTIC_BLOCK_RE = re.compile(r"[\u2C80-\u2CFF]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_WHITESPACE_RE = re.compile(r"\s+")
_COPTIC_TOKEN_RE = re.compile(r"[\u2C80-\u2CFF]+(?:['\u2019][\u2C80-\u2CFF]+)?")
_SUPPORTED_PUNCTUATION = set(".,;:!?()[]{}«»\"'’—-…/\\")
_DIALECTS = {"bohairic", "sahidic"}


@dataclass
class GrammarIssue:
    rule: str
    severity: str
    message: str
    token: Optional[str] = None
    position: Optional[int] = None


@dataclass
class GrammarCheckResult:
    text: str
    dialect: str
    score: float
    known_token_ratio: float
    token_count: int
    known_token_count: int
    mixed_script: bool
    issues: list[GrammarIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class GrammarChecker:
    """Rule-based Coptic surface-form validator."""

    def __init__(self, lexicon: Optional[Lexicon] = None) -> None:
        self.lexicon = lexicon or get_lexicon()

    @staticmethod
    def _tokenize_coptic(text: str) -> list[str]:
        return _COPTIC_TOKEN_RE.findall(text)

    @staticmethod
    def _has_only_supported_characters(text: str) -> bool:
        for char in text:
            if char.isspace():
                continue
            if _COPTIC_BLOCK_RE.search(char):
                continue
            if char in _SUPPORTED_PUNCTUATION:
                continue
            return False
        return True

    def _check_dialect_mismatch(self, token: str, dialect: str) -> list[GrammarIssue]:
        issues: list[GrammarIssue] = []
        matches = self.lexicon.lookup_coptic(token)
        if not matches:
            return issues

        valid_dialects = {entry for item in matches for entry in item.dialect}
        if valid_dialects and dialect not in valid_dialects:
            issues.append(
                GrammarIssue(
                    rule="dialect-mismatch",
                    severity="warning",
                    message=f"Token '{token}' is not attested for the selected dialect '{dialect}'.",
                    token=token,
                )
            )
        return issues

    def check(self, text: str, dialect: str = "bohairic") -> GrammarCheckResult:
        dialect = dialect.lower().strip() if dialect else "bohairic"
        if dialect not in _DIALECTS:
            dialect = "bohairic"

        issues: list[GrammarIssue] = []
        normalized_text = text.strip()

        if not normalized_text:
            issues.append(
                GrammarIssue(
                    rule="empty-input",
                    severity="error",
                    message="Input text is empty.",
                )
            )
            return GrammarCheckResult(
                text=text,
                dialect=dialect,
                score=0.0,
                known_token_ratio=0.0,
                token_count=0,
                known_token_count=0,
                mixed_script=False,
                issues=issues,
            )

        if _WHITESPACE_RE.search(normalized_text) and "  " in normalized_text:
            issues.append(
                GrammarIssue(
                    rule="excess-whitespace",
                    severity="info",
                    message="Input contains repeated whitespace.",
                )
            )

        has_coptic = bool(_COPTIC_BLOCK_RE.search(normalized_text))
        has_latin = bool(_LATIN_RE.search(normalized_text))
        mixed_script = has_coptic and has_latin

        if mixed_script:
            issues.append(
                GrammarIssue(
                    rule="mixed-script",
                    severity="error",
                    message="Text mixes Latin and Coptic characters.",
                )
            )

        if has_coptic and not self._has_only_supported_characters(normalized_text):
            issues.append(
                GrammarIssue(
                    rule="unsupported-character",
                    severity="error",
                    message="Text contains characters outside the supported Coptic/punctuation set.",
                )
            )

        tokens = self._tokenize_coptic(normalized_text)
        known_token_count = 0

        for index, token in enumerate(tokens):
            matches = self.lexicon.lookup_coptic(token)
            if matches:
                known_token_count += 1
                issues.extend(self._check_dialect_mismatch(token, dialect))
            else:
                issues.append(
                    GrammarIssue(
                        rule="unknown-token",
                        severity="warning",
                        message=f"Token '{token}' is not present in the lexicon.",
                        token=token,
                        position=index,
                    )
                )

        token_count = len(tokens)
        known_token_ratio = (known_token_count / token_count) if token_count else 0.0

        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.25
            elif issue.severity == "warning":
                score -= 0.08
            else:
                score -= 0.02

        score -= (1.0 - known_token_ratio) * 0.25
        score = max(0.0, min(1.0, score))

        return GrammarCheckResult(
            text=text,
            dialect=dialect,
            score=score,
            known_token_ratio=known_token_ratio,
            token_count=token_count,
            known_token_count=known_token_count,
            mixed_script=mixed_script,
            issues=issues,
        )


@lru_cache(maxsize=1)
def get_grammar_checker() -> GrammarChecker:
    """Singleton accessor for application-wide reuse."""
    return GrammarChecker()
