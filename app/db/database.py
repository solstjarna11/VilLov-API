# app/db/database.py

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, IS_SQLITE


class Base(DeclarativeBase):
    pass


engine_kwargs: dict = {
    "future": True,
    "pool_pre_ping": True,
}

# SQLite needs thread override in local development.
# Postgres on Render should not use this.
if IS_SQLITE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# print(f"[DB] Using database: {DATABASE_URL}")
engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()