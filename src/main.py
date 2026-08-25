import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from src.llm.client import call_model, get_system_prompt
from src.llm.parser import parse_model_output
from src.llm.schema import TriageRequest, TriageResponse

app = FastAPI()

LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"


def _validate_response(parsed: dict) -> TriageResponse | None:
    """Validate a parsed dict against TriageResponse. Returns the model or None."""
    try:
        return TriageResponse.model_validate(parsed)
    except ValidationError:
        return None


def _quarantine(input_text: str, raw_output: str, error: str) -> None:
    """Write a failed attempt to logs/quarantine.jsonl."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / "quarantine.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text": input_text,
        "prompt_version": "triage-v1",
        "raw_model_output": raw_output,
        "error": error,
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


@app.post("/triage", response_model=TriageResponse)
async def triage(request: TriageRequest):
    llm_stub = os.getenv("LLM_STUB")

    if llm_stub == "1":
        return TriageResponse(
            category="other",
            urgency="low",
            suggested_team="support",
            confidence=0.5,
            reason="stub response for testing",
        )

    system_prompt = get_system_prompt()

    # --- First attempt ---
    try:
        raw = call_model([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.text},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    parsed, parse_err = parse_model_output(raw)

    if parsed is not None:
        validated = _validate_response(parsed)
        if validated is not None:
            return validated

    # --- Repair attempt ---
    first_error = parse_err or "Pydantic validation failed"

    repair_instruction = (
        f"Your previous answer was rejected for this reason: {first_error}. "
        "Return only corrected JSON matching the schema, no other text."
    )

    try:
        raw_repair = call_model([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.text},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": repair_instruction},
        ])
    except Exception as e:
        # Repair call itself failed — quarantine the original failure
        _quarantine(request.text, raw, first_error)
        raise HTTPException(status_code=500, detail=f"LLM repair call failed: {e}")

    parsed_repair, repair_err = parse_model_output(raw_repair)

    if parsed_repair is not None:
        validated_repair = _validate_response(parsed_repair)
        if validated_repair is not None:
            return validated_repair

    # --- Both attempts failed — quarantine ---
    repair_error = repair_err or "Pydantic validation failed"
    _quarantine(request.text, raw_repair, repair_error)

    raise HTTPException(
        status_code=422,
        detail="Model output could not be validated after repair attempt",
    )
