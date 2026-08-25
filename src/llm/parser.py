import json
import re


def parse_model_output(raw_text: str) -> tuple[dict | None, str | None]:
    """Parse and extract a JSON object from raw model output.

    Returns (parsed_dict, None) on success, or (None, error_message) on failure.
    Never raises an exception.
    """
    text = raw_text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Find the first JSON object in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None, "No JSON object found in model output"

    json_str = match.group(0)

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

    return parsed, None
