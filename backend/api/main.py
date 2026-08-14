"""FastAPI backend for the Coptic translator (Phase 1 MVP)."""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.schemas import (
    HealthResponse,
    TranslationRequest,
    TranslationResponse,
)
from backend.translation.translator import (
    COP2EN_MODEL_NAME,
    EN2COP_MODEL_NAME,
    get_translator,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Coptic Translator API",
    description="English <-> Coptic (Bohairic / Sahidic) translation service.",
    version="0.1.0",
)

# Loosen for local dev; tighten before deploying publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    translator = get_translator()
    return HealthResponse(
        status="ok",
        model_en2cop_loaded=translator.en2cop_loaded,
        model_cop2en_loaded=translator.cop2en_loaded,
    )


@app.post("/translate", response_model=TranslationResponse)
def translate(request: TranslationRequest) -> TranslationResponse:
    translator = get_translator()
    try:
        output_text = translator.translate(
            text=request.text,
            direction=request.direction,
            dialect=request.dialect,
        )
    except Exception as exc:  # noqa: BLE001 - surface as a clean 500 for now
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    model_used = EN2COP_MODEL_NAME if request.direction == "en2cop" else COP2EN_MODEL_NAME

    return TranslationResponse(
        input_text=request.text,
        output_text=output_text,
        direction=request.direction,
        dialect=request.dialect,
        confidence=None,  # Phase 7 will populate this from the validation layer
        model=model_used,
    )
