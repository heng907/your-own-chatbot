from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import get_settings

"""
建立 SQLAlchemy engine（連線到 chat.db）。
"""
engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False},  # SQLite 需要這個
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency：取得 DB session，用完自動關閉"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
