import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "triage-v1.md"


def _get_client() -> OpenAI:
    load_dotenv()
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("LLM_API_KEY")
    return OpenAI(base_url=base_url, api_key=api_key)


def _get_model_name() -> str:
    load_dotenv()
    return os.getenv("LLM_MODEL", "openrouter/free")


def get_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def call_model(messages: list[dict]) -> str:
    """Call the LLM with a full messages list. Returns raw string content."""
    client = _get_client()
    model_name = _get_model_name()

    response = client.chat.completions.create(
        model=model_name,
        temperature=0.2,
        messages=messages,
    )

    return response.choices[0].message.content


def get_llm_response(user_text: str) -> str:
    """Convenience function: load prompt from disk, call model, return raw text."""
    system_prompt = get_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]
    return call_model(messages)
