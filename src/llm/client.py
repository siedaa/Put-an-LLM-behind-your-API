import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "triage-v1.md"


def get_llm_response(user_text: str) -> str:
    load_dotenv()

    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("LLM_API_KEY")
    model_name = os.getenv("LLM_MODEL", "openrouter/free")

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    client = OpenAI(base_url=base_url, api_key=api_key)

    response = client.chat.completions.create(
        model=model_name,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )

    return response.choices[0].message.content
