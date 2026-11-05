import os, uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import func
from ..core import get_db, current_user, rate_limit
from ..models import DebateSession, DebateEvaluation
from ..services import ai_service as ai

router = APIRouter(prefix="/api", tags=["debates"])
CATS = ["Technology", "Education", "Politics", "Economics", "Environment", "Society", "Ethics", "Science", "International Relations", "Business", "Artificial Intelligence", "Random"]
DURATIONS = {30, 120, 300, 600}
MAX_AUDIO = 25 * 1024 * 1024
UPLOADS = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")

class Start(BaseModel):
    category: str = "Random"; duration_seconds: int

def s_out(s):
    return {"id": s.id, "topic": s.topic, "category": s.category, "assigned_side": s.assigned_side,
            "duration_seconds": s.duration_seconds, "input_mode": s.input_mode, "status": s.status,
            "started_at": s.started_at, "overall_score": s.evaluation.overall_score if s.evaluation else None}

def mine(db, user, sid):
    s = db.query(DebateSession).filter_by(id=sid, user_id=user.id).first()
    if not s: raise HTTPException(404, "Debate not found")
    return s

def ev_out(e):
    return {c.name: getattr(e, c.name) for c in e.__table__.columns}

@router.post("/debates/start", status_code=201)
async def start(d: Start, u=Depends(current_user), db=Depends(get_db)):
    if d.category not in CATS or d.duration_seconds not in DURATIONS: raise HTTPException(422, "Invalid category or duration")
    rate_limit(u, 30)
    s = DebateSession(user_id=u.id, topic=await ai.generate_debate_topic(d.category), category=d.category,
                      assigned_side=ai.assign_debate_side(), duration_seconds=d.duration_seconds)
    db.add(s); db.commit()
    return s_out(s)

@router.get("/debates")
def list_debates(q: str = "", category: str = "", side: str = "", sort: str = "date_desc", page: int = 1, size: int = 10,
                 u=Depends(current_user), db=Depends(get_db)):
    qs = db.query(DebateSession).filter(DebateSession.user_id == u.id, DebateSession.status == "completed")
    if q: qs = qs.filter(DebateSession.topic.like(f"%{q}%"))
    if category: qs = qs.filter(DebateSession.category == category)
    if side: qs = qs.filter(DebateSession.assigned_side == side)
    qs = qs.outerjoin(DebateEvaluation)
    order = {"date_asc": DebateSession.started_at.asc(), "score_desc": DebateEvaluation.overall_score.desc(),
             "score_asc": DebateEvaluation.overall_score.asc()}.get(sort, DebateSession.started_at.desc())
    total = qs.count()
    items = qs.order_by(order).offset((max(page, 1) - 1) * size).limit(min(size, 50)).all()
    return {"total": total, "items": [s_out(s) for s in items]}

@router.get("/debates/{sid}")
def get_debate(sid: int, u=Depends(current_user), db=Depends(get_db)):
    s = mine(db, u, sid)
    return {**s_out(s), "transcript": s.transcript}

@router.delete("/debates/{sid}", status_code=204)
def delete(sid: int, u=Depends(current_user), db=Depends(get_db)):
    s = mine(db, u, sid)
    if s.recording_path and os.path.exists(s.recording_path): os.remove(s.recording_path)
    db.delete(s); db.commit()

@router.post("/debates/{sid}/submit")
async def submit(sid: int, mode: str = Form(...), text: Optional[str] = Form(None), audio: Optional[UploadFile] = File(None),
                 u=Depends(current_user), db=Depends(get_db)):
    s = mine(db, u, sid)
    if s.status == "completed": raise HTTPException(409, "Already submitted")
    if (datetime.utcnow() - s.started_at).total_seconds() > s.duration_seconds + 600:  # prep + upload grace
        raise HTTPException(408, "Session expired")
    rate_limit(u)
    if mode == "voice":
        if not audio or not audio.content_type.startswith(("audio/", "video/webm")): raise HTTPException(422, "Audio file required")
        data = await audio.read()
        if len(data) > MAX_AUDIO: raise HTTPException(413, "Audio too large")
        os.makedirs(UPLOADS, exist_ok=True)
        s.recording_path = os.path.abspath(os.path.join(UPLOADS, f"{uuid.uuid4().hex}.webm"))
        open(s.recording_path, "wb").write(data)
        transcript = await ai.transcribe_argument("speech.webm", data, audio.content_type)
    elif mode == "text":
        transcript = (text or "").strip()
        if len(transcript.split()) > s.duration_seconds * 4: raise HTTPException(422, "Text exceeds time limit")
    else: raise HTTPException(422, "Invalid mode")
    if len(transcript.split()) < 10: raise HTTPException(422, "Argument too short to evaluate")
    ev = await ai.evaluate_argument(s.topic, s.assigned_side, transcript, s.duration_seconds, mode)
    s.transcript, s.input_mode, s.status, s.completed_at = transcript, mode, "completed", datetime.utcnow()
    db.add(DebateEvaluation(session_id=s.id, overall_score=ai.weighted_overall(ev),
        logical_reasoning_score=ev.logical_reasoning, argument_strength_score=ev.argument_strength, clarity_score=ev.clarity,
        structure_score=ev.structure, relevance_score=ev.relevance, evidence_score=ev.evidence, delivery_score=ev.delivery,
        overall_assessment=ev.overall_assessment, strengths=ev.strengths, weaknesses=ev.weaknesses,
        logical_fallacies=[f.model_dump() for f in ev.logical_fallacies], missed_opportunities=ev.missed_opportunities,
        improvement_suggestions=ev.improvement_suggestions, improved_argument=ev.improved_argument, final_verdict=ev.final_verdict))
    db.commit()
    return {"id": s.id}

@router.get("/evaluations/{sid}")
def evaluation(sid: int, u=Depends(current_user), db=Depends(get_db)):
    s = mine(db, u, sid)
    if not s.evaluation: raise HTTPException(404, "No evaluation yet")
    return {"session": {**s_out(s), "transcript": s.transcript}, "evaluation": ev_out(s.evaluation)}

@router.get("/statistics/overview")
def overview(u=Depends(current_user), db=Depends(get_db)):
    base = db.query(DebateSession).filter_by(user_id=u.id, status="completed")
    n, secs = base.count(), base.with_entities(func.coalesce(func.sum(DebateSession.duration_seconds), 0)).scalar()
    E = DebateEvaluation
    row = db.query(func.avg(E.overall_score), func.max(E.overall_score), func.avg(E.logical_reasoning_score), func.avg(E.argument_strength_score),
                   func.avg(E.clarity_score), func.avg(E.structure_score), func.avg(E.relevance_score), func.avg(E.evidence_score),
                   func.avg(E.delivery_score)).join(DebateSession).filter(DebateSession.user_id == u.id).one()
    keys = ["logical_reasoning", "argument_strength", "clarity", "structure", "relevance", "evidence", "delivery"]
    return {"total_debates": n, "total_speaking_seconds": int(secs), "average_score": round(row[0] or 0, 1), "highest_score": row[1] or 0,
            "skills": {k: round(float(v), 1) if v is not None else None for k, v in zip(keys, row[2:])}}

@router.get("/statistics/progress")
def progress(u=Depends(current_user), db=Depends(get_db)):
    rows = db.query(DebateSession.id, DebateSession.started_at, E_score()).join(DebateEvaluation).filter(DebateSession.user_id == u.id).order_by(DebateSession.started_at).limit(100).all()
    pts = [{"id": r[0], "date": r[1], "score": r[2]} for r in rows]
    half = len(pts) // 2
    avg = lambda a: sum(p["score"] for p in a) / len(a) if a else 0
    return {"points": pts, "trend": round(avg(pts[half:]) - avg(pts[:half]), 1) if half else 0}

def E_score(): return DebateEvaluation.overall_score
