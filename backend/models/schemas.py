"""Pydantic schemas shared across the API."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Direction = Literal["en2cop", "cop2en"]
Dialect = Literal["bohairic", "sahidic"]


class RetrievalHit(BaseModel):
    source: Literal["corpus", "lexicon"]
    title: str
    text: str
    score: float
    dialect: Optional[str] = None
    source_ref: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GrammarIssue(BaseModel):
    rule: str
    severity: Literal["info", "warning", "error"]
    message: str
    token: Optional[str] = None
    position: Optional[int] = None


class GrammarCheckResponse(BaseModel):
    text: str
    dialect: Dialect
    score: float
    known_token_ratio: float
    token_count: int
    known_token_count: int
    mixed_script: bool
    issues: list[GrammarIssue] = Field(default_factory=list)


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to translate.")
    direction: Direction = Field(
        ..., description="'en2cop' for English->Coptic, 'cop2en' for Coptic->English."
    )
    dialect: Dialect = Field(
        default="bohairic",
        description="Target Coptic dialect (used for en2cop; informational for cop2en).",
    )


class ConfidenceBreakdown(BaseModel):
    overall: float = Field(
        ...,
        description="Weighted combination of the components below, 0-1. A documented heuristic, not a calibrated probability.",
    )
    label: Literal["High", "Moderate", "Low", "Very Low"]
    model_confidence: Optional[float] = None
    dictionary_coverage: Optional[float] = None
    grammar_score: Optional[float] = None
    retrieval_support: Optional[float] = None
    weights: dict[str, float] = Field(default_factory=dict)


class TranslationResponse(BaseModel):
    input_text: str
    output_text: str
    direction: Direction
    dialect: Dialect
    confidence: Optional[float] = Field(
        default=None,
        description="Raw model confidence, 0-1, as reported by the translation model itself. Not independently calibrated - treat as one weak signal, not ground truth.",
    )
    dictionary_coverage: Optional[float] = Field(
        default=None,
        description="Fraction (0-1) of English input words found in our own lexicon (Phase 3). A separate, independent signal from model confidence - low coverage means the lexicon has nothing to say either way, not that the translation is necessarily wrong.",
    )
    retrieval_hits: list[RetrievalHit] = Field(
        default_factory=list,
        description="Top retrieval matches used to ground translation and later validation.",
    )
    model: str
    validation: Optional[ConfidenceBreakdown] = Field(
        default=None,
        description="Phase 7 combined confidence breakdown. See ConfidenceBreakdown for the components.",
    )


class HealthResponse(BaseModel):
    status: str
    model_en2cop_loaded: bool
    model_cop2en_loaded: bool


class LabNote(BaseModel):
    id: int
    date: str
    category: Literal["Model", "Corpus", "Grammar", "Eval"]
    title: str
    content: str
    metric_label: Optional[str] = None
    metric_value: Optional[float] = None


class LabNoteCreate(BaseModel):
    title: str = Field(..., min_length=1)
    category: Literal["Model", "Corpus", "Grammar", "Eval"] = "Model"
    content: str = Field(..., min_length=1)
    metric_label: Optional[str] = None
    metric_value: Optional[float] = Field(default=None, ge=0, le=1)


class LexiconEntryResponse(BaseModel):
    coptic: str
    lemma: str
    english: list[str]
    dialect: list[str]
    part_of_speech: Optional[str] = None
    gender: Optional[str] = None
    sources: Optional[list[str]] = None


class ManuscriptSummary(BaseModel):
    source: str
    dialect: str
    sentence_count: int
    annotated: bool
    sample_coptic: str
    sample_english: str
