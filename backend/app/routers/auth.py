from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import or_
from ..core import get_db, hash_pw, check_pw, make_token, current_user
from ..models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

class Register(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,40}$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str
    @model_validator(mode="after")
    def same(self):
        if self.password != self.confirm_password: raise ValueError("Passwords do not match")
        return self
class Login(BaseModel):
    identifier: str; password: str

def pub(u): return {"id": u.id, "full_name": u.full_name, "username": u.username, "email": u.email}

@router.post("/register", status_code=201)
def register(d: Register, db=Depends(get_db)):
    if db.query(User).filter(or_(User.email == d.email, User.username == d.username)).first():
        raise HTTPException(409, "Username or email already in use")
    u = User(full_name=d.full_name, username=d.username, email=d.email, password_hash=hash_pw(d.password))
    db.add(u); db.commit()
    return {"token": make_token(u.id), "user": pub(u)}

@router.post("/login")
def login(d: Login, db=Depends(get_db)):
    u = db.query(User).filter(or_(User.email == d.identifier, User.username == d.identifier)).first()
    if not u or not check_pw(d.password, u.password_hash): raise HTTPException(401, "Wrong credentials")
    return {"token": make_token(u.id), "user": pub(u)}

@router.post("/logout")
def logout(_=Depends(current_user)): return {"ok": True}

@router.get("/me")
def me(u=Depends(current_user)): return pub(u)
