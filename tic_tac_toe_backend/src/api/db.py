"""
Database setup and session management for SQLite using SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from .models import Base

DATABASE_URL = os.getenv("TICTACTOE_SQLITE_URL", "sqlite:///./tictactoe.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
