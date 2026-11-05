from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .core import Base, engine, settings
from . import models
from .routers import auth, debates

Base.metadata.create_all(engine)  # swap for Alembic migrations in production
app = FastAPI(title="Debatrix API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors.split(","), allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(debates.router)
