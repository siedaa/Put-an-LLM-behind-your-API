import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "triage-v1.md"


@dataclass
class ModelResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int


def _get_client() -> OpenAI:
    load_dotenv()
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("LLM_API_KEY")
    # max_retries=0: we implement our own retry logic in retry.py
    # to avoid double-retrying (SDK retries + our retries stacking).
    return OpenAI(base_url=base_url, api_key=api_key, timeout=30.0, max_retries=0)


def _get_model_name() -> str:
    load_dotenv()
    return os.getenv("LLM_MODEL", "openrouter/free")


def get_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def call_model(messages: list[dict]) -> ModelResponse:
    """Call the LLM with a full messages list. Returns a ModelResponse."""
    client = _get_client()
    model_name = _get_model_name()

    start = time.monotonic()
    response = client.chat.completions.create(
        model=model_name,
        temperature=0.2,
        messages=messages,
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    usage = response.usage
    return ModelResponse(
        content=response.choices[0].message.content,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        duration_ms=duration_ms,
    )


def get_llm_response(user_text: str) -> ModelResponse:
    """Convenience function: load prompt from disk, call model, return ModelResponse."""
    system_prompt = get_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]
    return call_model(messages)
