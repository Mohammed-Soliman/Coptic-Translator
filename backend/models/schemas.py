"""Pydantic schemas shared across the API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Direction = Literal["en2cop", "cop2en"]
Dialect = Literal["bohairic", "sahidic"]


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to translate.")
    direction: Direction = Field(
        ..., description="'en2cop' for English->Coptic, 'cop2en' for Coptic->English."
    )
    dialect: Dialect = Field(
        default="bohairic",
        description="Target Coptic dialect (used for en2cop; informational for cop2en).",
    )


class TranslationResponse(BaseModel):
    input_text: str
    output_text: str
    direction: Direction
    dialect: Dialect
    confidence: Optional[float] = Field(
        default=None, description="Placeholder confidence score, 0-1. Not yet calibrated."
    )
    model: str


class HealthResponse(BaseModel):
    status: str
    model_en2cop_loaded: bool
    model_cop2en_loaded: bool
