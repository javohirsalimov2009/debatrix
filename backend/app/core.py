import time, jwt, bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    db_url: str = "sqlite:///debatrix.db"
    jwt_secret: str
    cors: str = "http://localhost:5173"
    ai_api_key: str = ""
    ai_model: str = "openai/gpt-oss-120b"
    ai_transcription_model: str = "whisper-large-v3-turbo"
settings = Settings()
database_url = make_url(settings.db_url)
if database_url.get_backend_name() == "sqlite" and database_url.database not in (None, "", ":memory:"):
    database_path = Path(database_url.database)
    if not database_path.is_absolute():
        database_path = Path(__file__).resolve().parents[1] / database_path
    database_url = database_url.set(database=str(database_path))
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if database_url.get_backend_name() == "sqlite" else {},
)
if database_url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, connection_record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p, h): return bcrypt.checkpw(p.encode(), h.encode())
def make_token(uid): return jwt.encode({"sub": str(uid), "exp": datetime.utcnow() + timedelta(days=7)}, settings.jwt_secret, "HS256")

def current_user(cred=Depends(HTTPBearer()), db=Depends(get_db)):
    from .models import User
    try: uid = int(jwt.decode(cred.credentials, settings.jwt_secret, ["HS256"])["sub"])
    except Exception: raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "User not found")
    return u

_hits = {}
def rate_limit(user, limit=10, window=3600):
    now = time.time(); h = [t for t in _hits.get(user.id, []) if now - t < window]
    if len(h) >= limit: raise HTTPException(429, "Too many AI requests. Try again later.")
    _hits[user.id] = h + [now]
