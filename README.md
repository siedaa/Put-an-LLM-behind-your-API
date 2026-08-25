# support-message-classifier-backend

## Setup

Follow these steps to set up and run the throwaway LLM connection test script:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in a real OpenRouter key for `LLM_API_KEY`:
   ```bash
   cp .env.example .env
   ```

3. **Run the Test Script**:
   Execute the hello script to verify your connection to the LLM via OpenRouter:
   ```bash
   python src/llm/hello.py
   ```

## Testing Stage 1

1. **Start the server** (with stub mode enabled):
   ```bash
   set LLM_STUB=1
   uvicorn src.main:app --reload
   ```

2. **Valid request** (should return `200`):
   ```bash
   curl -X POST http://127.0.0.1:8000/triage -H "Content-Type: application/json" -d "{\"text\": \"I was charged twice for my subscription\"}"
   ```

3. **Invalid request — missing `text`** (should return `422`):
   ```bash
   curl -X POST http://127.0.0.1:8000/triage -H "Content-Type: application/json" -d "{}"
   ```
