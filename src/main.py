import os

from fastapi import FastAPI, HTTPException

from src.llm.schema import TriageRequest, TriageResponse

app = FastAPI()


@app.post("/triage", response_model=TriageResponse)
async def triage(request: TriageRequest) -> TriageResponse:
    llm_stub = os.getenv("LLM_STUB")

    if llm_stub == "1":
        return TriageResponse(
            category="other",
            urgency="low",
            suggested_team="support",
            confidence=0.5,
            reason="stub response for testing",
        )

    raise HTTPException(
        status_code=501,
        detail="model integration not yet built",
    )
