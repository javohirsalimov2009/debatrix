import asyncio, json, random, httpx
from typing import Optional, List
from pydantic import BaseModel, Field, ValidationError
from fastapi import HTTPException
from ..core import settings

WEIGHTS = {"logical_reasoning": 20, "argument_strength": 20, "clarity": 15, "structure": 15, "relevance": 10, "evidence": 10, "delivery": 10}

class Fallacy(BaseModel):
    name: str; quote: str = ""; explanation: str
class Evaluation(BaseModel):
    logical_reasoning: float = Field(ge=0, le=10); argument_strength: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10); structure: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10); evidence: float = Field(ge=0, le=10)
    delivery: Optional[float] = Field(default=None, ge=0, le=10)
    overall_assessment: str; strengths: List[str]; weaknesses: List[str]
    logical_fallacies: List[Fallacy] = []; missed_opportunities: List[str]
    improvement_suggestions: List[str]; improved_argument: str; final_verdict: str

def weighted_overall(e: Evaluation) -> float:
    w = {k: v for k, v in WEIGHTS.items() if getattr(e, k) is not None}
    tot = sum(w.values())
    return round(sum(getattr(e, k) * 10 * v / tot for k, v in w.items()), 1)

GROQ_API_URL = "https://api.groq.com/openai/v1"

async def _request(path, *, timeout=90, **kwargs):
    if not settings.ai_api_key or not settings.ai_api_key.startswith("gsk_"):
        raise HTTPException(503, "Set AI_API_KEY in backend/.env to your Groq API key (starts with gsk_), then restart the backend.")
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    f"{GROQ_API_URL}/{path}",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    **kwargs,
                )
            except httpx.TimeoutException as exc:
                raise HTTPException(504, "Groq request timed out. Please try again.") from exc
            except httpx.RequestError as exc:
                raise HTTPException(503, "Could not connect to Groq. Please check your connection and try again.") from exc
            status = response.status_code
            if status in (408, 500, 502, 503, 504) and attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            if status in (401, 403):
                raise HTTPException(503, "Groq rejected the API key. Check AI_API_KEY and model access in your Groq account, then restart the backend.")
            if status == 429:
                delay = response.headers.get("Retry-After", "60")
                raise HTTPException(429, "Groq free-plan request limit reached. Please wait and try again.", headers={"Retry-After": delay})
            if status == 408 or status >= 500:
                raise HTTPException(503, "Groq is temporarily unavailable. Please try again shortly.", headers={"Retry-After": "15"})
            if status >= 400:
                raise HTTPException(502, "Groq could not process the request. Check AI_MODEL and AI_TRANSCRIPTION_MODEL in backend/.env and the uploaded audio format.")
            try:
                return response.json()
            except ValueError as exc:
                raise HTTPException(502, "Groq returned an invalid response. Please retry.") from exc

async def _chat(system, user, json_mode=True):
    payload = {
        "model": settings.ai_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.4,
        "max_completion_tokens": 4096,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    result = await _request("chat/completions", json=payload)
    try:
        text = result["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty content")
        return text.strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(502, "Groq returned an empty or invalid response. Please retry.") from exc

async def generate_debate_topic(category: str) -> str:
    cat = "any interesting field" if category == "Random" else category
    out = await _chat("You write debate motions. Reply as JSON: {\"motion\": str}. The motion must be a single balanced, debatable statement with strong arguments on both sides. No trivial, vague or one-sided motions.",
                      f"Category: {cat}. Seed: {random.randint(0, 99999)}")
    try:
        motion = json.loads(out)["motion"]
        if not isinstance(motion, str) or not motion.strip():
            raise ValueError("Empty motion")
        return motion.strip()
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, "Groq returned an invalid debate topic. Please retry.") from exc

def assign_debate_side() -> str:
    return random.choice(["AFFIRMATIVE", "OPPOSITION"])

async def transcribe_argument(filename: str, data: bytes, mime: str) -> str:
    result = await _request(
        "audio/transcriptions", timeout=120,
        data={"model": settings.ai_transcription_model, "response_format": "json", "temperature": "0"},
        files={"file": (filename, data, mime.split(";")[0].strip())},
    )
    text = result.get("text") if isinstance(result, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(502, "Groq returned an empty transcript. Please record your speech again.")
    return text.strip()

RUBRIC = """You are a strict, fair debate adjudicator. Judge ONLY the quality of the argument for the assigned side, never your own opinion of the motion.
Score each criterion 0-10 (integers or .5): logical_reasoning (consistency, valid inference, fallacies), argument_strength (relevance, depth, persuasiveness), clarity, structure (intro, claims, evidence, conclusion, transitions), relevance (addresses motion and assigned side), evidence (quality of examples/evidence), delivery (ONLY from transcript fluency cues: pace, filler words, hesitations; null if input_mode is text).
Rules: length is not quality; ignore fancy vocabulary if the reasoning is weak; a typical decent speech scores 5-6; 9+ is exceptional. Never invent evidence or citations; label unverifiable claims as unsupported. Only report logical fallacies actually present, quoting the transcript. Distinguish factual errors, unsupported claims and reasonable opinions. Speeches far shorter than the time allows should be penalised for depth. Do not comment on body language.
improved_argument must keep the user's original position and be realistic for the time limit.
Reply as JSON with keys: logical_reasoning, argument_strength, clarity, structure, relevance, evidence, delivery, overall_assessment, strengths[], weaknesses[], logical_fallacies[{name,quote,explanation}], missed_opportunities[], improvement_suggestions[], improved_argument, final_verdict."""

async def evaluate_argument(topic, side, transcript, duration, mode) -> Evaluation:
    words = len(transcript.split())
    user = f"Motion: {topic}\nAssigned side: {side}\nTime allowed: {duration}s\ninput_mode: {mode}\nWord count: {words}\nTranscript:\n\"\"\"{transcript}\"\"\""
    for _ in range(2):
        try:
            ev = Evaluation(**json.loads(await _chat(RUBRIC, user)))
            if mode == "text": ev.delivery = None
            return ev
        except (ValidationError, ValueError, KeyError, TypeError):
            continue
    raise HTTPException(502, "AI returned an invalid evaluation. Please retry.")
