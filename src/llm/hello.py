import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Retrieve settings
base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
api_key = os.getenv("LLM_API_KEY")
model_name = os.getenv("LLM_MODEL", "openrouter/free")

if not api_key:
    print("Warning: LLM_API_KEY is not set in the environment or .env file.")

# Create the OpenAI client
client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

try:
    # Request completion
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "user", "content": "Reply with exactly the word: ready"}
        ]
    )

    # Print the response content
    if response.choices:
        print(response.choices[0].message.content)
    else:
        print("No choices returned in the response.")
except Exception as e:
    print(f"Error calling LLM: {e}")
