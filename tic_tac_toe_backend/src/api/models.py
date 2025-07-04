"""
ORM models and authentication helpers for the Tic Tac Toe backend.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# --- Constants for JWT ---
SECRET_KEY = "please_change_this_in_env_later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 6 * 60 # 6 hours

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta]=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# --- SQLAlchemy ORM Definitions ---
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    games_won = Column(Integer, default=0)
    games_lost = Column(Integer, default=0)
    games_tied = Column(Integer, default=0)

    games_as_x = relationship("Game", back_populates="user_x", foreign_keys="[Game.x_user_id]")
    games_as_o = relationship("Game", back_populates="user_o", foreign_keys="[Game.o_user_id]")

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    x_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    o_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    board = Column(String(9), default="         ")         # 9 chars, 'X', 'O', or ' '
    turn = Column(String(1), default="X")                 # 'X' or 'O'
    is_complete = Column(Boolean, default=False)
    winner = Column(String(1), nullable=True)             # 'X', 'O', 'T' (tie), or None

    user_x = relationship("User", foreign_keys=[x_user_id], back_populates="games_as_x")
    user_o = relationship("User", foreign_keys=[o_user_id], back_populates="games_as_o")

# --- Pydantic schemas for API ---
class UserCreate(BaseModel):
    username: str = Field(..., description="Username (unique)")
    password: str = Field(..., description="Password (plaintext)")

class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class GameCreate(BaseModel):
    opponent_username: Optional[str] = None

class GameMove(BaseModel):
    position: int = Field(..., ge=0, le=8, description="Board position to place (0-8)")

class GameOut(BaseModel):
    id: int
    x_user: str
    o_user: Optional[str]
    board: str
    turn: str
    is_complete: bool
    winner: Optional[str]

    class Config:
        orm_mode = True

class LeaderboardEntry(BaseModel):
    username: str
    won: int
    lost: int
    tied: int

class Leaderboard(BaseModel):
    entries: List[LeaderboardEntry]
