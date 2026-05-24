from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401 - ensure models are registered on Base.metadata


def _engine_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    return {}


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_database_url = database_url or settings.database_url

    return create_engine(
        resolved_database_url,
        echo=settings.database_echo,
        future=True,
        pool_pre_ping=True,
        connect_args=_engine_connect_args(resolved_database_url),
    )


engine = create_database_engine()
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


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    """
    Creates tables for local/dev fallback.

    Production deployments should prefer Alembic migrations, but this helper is
    safe for test/local initialization and keeps Sprint 16 non-breaking.
    """
    Base.metadata.create_all(bind=engine)


def get_database_readiness() -> dict:
    database_url = settings.database_url
    masked_database_url = _mask_database_url(database_url)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return {
            "success": True,
            "ready": False,
            "database_url": masked_database_url,
            "database_engine": _database_engine_name(database_url),
            "message": "Database connection check failed.",
            "error": str(exc),
        }

    return {
        "success": True,
        "ready": True,
        "database_url": masked_database_url,
        "database_engine": _database_engine_name(database_url),
        "message": "Database connection check succeeded.",
        "error": None,
    }


def _database_engine_name(database_url: str) -> str:
    if database_url.startswith("postgresql"):
        return "postgresql"

    if database_url.startswith("sqlite"):
        return "sqlite"

    return database_url.split(":", 1)[0] if ":" in database_url else "unknown"


def _mask_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url

    scheme, rest = database_url.split("://", 1)
    _credentials, host_part = rest.split("@", 1)

    return f"{scheme}://***:***@{host_part}"