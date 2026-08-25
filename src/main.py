import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from openai import APITimeoutError

from src.llm.client import ModelResponse, call_model, get_system_prompt
from src.llm.parser import parse_model_output
from src.llm.retry import call_with_retry
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


def _log_cost(model_response: ModelResponse, needed_repair: bool) -> None:
    """Write a cost log entry to logs/cost.jsonl."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / "cost.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": "triage-v1",
        "model": os.getenv("LLM_MODEL", "unknown"),
        "input_tokens": model_response.prompt_tokens,
        "output_tokens": model_response.completion_tokens,
        "duration_ms": model_response.duration_ms,
        "needed_repair": needed_repair,
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _raise_provider_error(exc: Exception) -> None:
    """Convert a provider exception into a clean HTTP error."""
    if isinstance(exc, APITimeoutError):
        raise HTTPException(status_code=504, detail="LLM request timed out")
    raise HTTPException(
        status_code=502,
        detail=f"LLM provider error: {exc}",
    )


@app.post("/triage", response_model=TriageResponse)
async def triage(request: TriageRequest):
    llm_stub = os.getenv("LLM_STUB")
    llm_enabled = os.getenv("LLM_ENABLED", "true")

    if llm_stub == "1":
        return TriageResponse(
            category="other",
            urgency="low",
            suggested_team="support",
            confidence=0.5,
            reason="stub response for testing",
        )

    if llm_enabled == "false":
        raise HTTPException(
            status_code=503,
            detail="LLM feature temporarily disabled",
        )

    system_prompt = get_system_prompt()
    needed_repair = False

    # --- First attempt ---
    try:
        resp = call_with_retry(lambda: call_model([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.text},
        ]))
    except Exception as e:
        _raise_provider_error(e)

    parsed, parse_err = parse_model_output(resp.content)

    if parsed is not None:
        validated = _validate_response(parsed)
        if validated is not None:
            _log_cost(resp, needed_repair=False)
            return validated

    # --- Repair attempt ---
    needed_repair = True
    first_error = parse_err or "Pydantic validation failed"

    repair_instruction = (
        f"Your previous answer was rejected for this reason: {first_error}. "
        "Return only corrected JSON matching the schema, no other text."
    )

    try:
        resp_repair = call_with_retry(lambda: call_model([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.text},
            {"role": "assistant", "content": resp.content},
            {"role": "user", "content": repair_instruction},
        ]))
    except Exception as e:
        _quarantine(request.text, resp.content, first_error)
        _raise_provider_error(e)

    parsed_repair, repair_err = parse_model_output(resp_repair.content)

    if parsed_repair is not None:
        validated_repair = _validate_response(parsed_repair)
        if validated_repair is not None:
            _log_cost(resp_repair, needed_repair=True)
            return validated_repair

    # --- Both attempts failed — quarantine ---
    repair_error = repair_err or "Pydantic validation failed"
    _quarantine(request.text, resp_repair.content, repair_error)
    _log_cost(resp_repair, needed_repair=True)

    raise HTTPException(
        status_code=422,
        detail="Model output could not be validated after repair attempt",
    )
