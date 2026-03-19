from datetime import datetime, timedelta
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt
import bcrypt
from pydantic import BaseModel

from app.core.config import settings
from app.models.base import get_db
from app.models.user import User
from app.repositories.user_repository import user_repository

router = APIRouter()

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

class UserRegister(BaseModel):
    user_id: str
    password: str
    username: Optional[str] = None
    role: Literal["student", "teacher"] = "student" # 只允許註冊學生或老師

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.post("/register")
def register(req: UserRegister, db: Session = Depends(get_db)):
    # 再次檢查是否為 admin (雙重防護)
    if req.role == "admin":
         raise HTTPException(status_code=403, detail="Admin role cannot be registered.")

    db_user = user_repository.get_by_user_id(db, req.user_id)
    if db_user:
        raise HTTPException(status_code=400, detail="User ID already registered")
    
    new_user = user_repository.create(
        db,
        user_id=req.user_id,
        username=req.username or req.user_id,
        hashed_password=hash_password(req.password),
        role=req.role,
    )
    return {"message": "User registered successfully", "user_id": new_user.user_id}

@router.post("/login")
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # 這裡的 form_data 會自動包含 username 與 password
    user = user_repository.get_by_user_id(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect user ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={
        "sub": user.user_id,
        "role": user.role,
        "username": user.username
    })
    return {"access_token": access_token, "token_type": "bearer"}
