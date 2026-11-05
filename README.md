# Debatrix
## Setup
1. Database: SQLite stores data locally in `backend/debatrix.db`. The file and tables are created automatically on startup; no database server is needed.
2. Backend: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env` (fill JWT_SECRET and AI_API_KEY) then `uvicorn app.main:app --reload`. Tables are created on startup.
3. Frontend: `cd frontend && npm install && npm run dev` -> http://localhost:5173
## AI provider
Groq handles debate topics and evaluations with `openai/gpt-oss-120b`, and audio transcription with `whisper-large-v3-turbo`, using the existing httpx dependency.

1. Create a Groq account at https://console.groq.com and stay on the Free Plan.
2. Create an API key at https://console.groq.com/keys.
3. In backend/.env, replace AI_API_KEY with that Groq key (starts with gsk_). Set AI_MODEL=openai/gpt-oss-120b and AI_TRANSCRIPTION_MODEL=whisper-large-v3-turbo.
4. Stop the backend with Ctrl+C and restart it. In PowerShell, from the project root: `cd backend`, then `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
5. Start a debate and submit a text argument, then try a voice recording.

The Free Plan has rate limits. If a limit is reached, wait before retrying; a paid upgrade is not required. A Gemini key cannot authenticate with Groq. Never commit your real .env or API keys.
