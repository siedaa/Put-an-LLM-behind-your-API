import os

from fastapi import FastAPI, HTTPException
from starlette.responses import PlainTextResponse

from src.llm.client import get_llm_response
from src.llm.schema import TriageRequest, TriageResponse

app = FastAPI()


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

    try:
        raw = get_llm_response(request.text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM call failed: {e}",
        )
    return PlainTextResponse(content=raw)
