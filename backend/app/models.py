from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON, Enum, Index
from sqlalchemy.orm import relationship
from .core import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    username = Column(String(40), unique=True, nullable=False, index=True)
    email = Column(String(190), unique=True, nullable=False, index=True)
    password_hash = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DebateSession(Base):
    __tablename__ = "debate_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(300), nullable=False)
    category = Column(String(60), nullable=False)
    assigned_side = Column(Enum("AFFIRMATIVE", "OPPOSITION"), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    input_mode = Column(Enum("voice", "text"))
    transcript = Column(Text)
    recording_path = Column(String(255))
    status = Column(Enum("started", "completed"), default="started")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    evaluation = relationship("DebateEvaluation", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    __table_args__ = (Index("ix_user_started", "user_id", "started_at"),)

class DebateEvaluation(Base):
    __tablename__ = "debate_evaluations"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("debate_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_score = Column(Float, nullable=False)
    logical_reasoning_score = Column(Float); argument_strength_score = Column(Float)
    clarity_score = Column(Float); structure_score = Column(Float); relevance_score = Column(Float)
    evidence_score = Column(Float); delivery_score = Column(Float)
    overall_assessment = Column(Text); final_verdict = Column(Text); improved_argument = Column(Text)
    strengths = Column(JSON); weaknesses = Column(JSON); logical_fallacies = Column(JSON)
    missed_opportunities = Column(JSON); improvement_suggestions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
