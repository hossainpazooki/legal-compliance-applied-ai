"""Database connection management for SQLModel ORM.

Supports both SQLite (local dev) and PostgreSQL (production) via DATABASE_URL.
"""

import os
from pathlib import Path
from typing import Generator

from sqlmodel import Session, create_engine, SQLModel

# Default database path (SQLite)
_DB_PATH: Path | None = None
_engine = None


def get_database_url() -> str:
    """Get database URL from environment or default to SQLite.

    Handles Railway's postgres:// URL format by converting to postgresql://.
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Railway uses postgres:// but SQLAlchemy requires postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    # Default to SQLite for local development
    db_path = get_db_path()
    return f"sqlite:///{db_path}"


def get_db_path() -> Path:
    """Get the SQLite database file path (used when DATABASE_URL not set)."""
    global _DB_PATH
    if _DB_PATH is None:
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        _DB_PATH = data_dir / "ke_workbench.db"
    return _DB_PATH


def set_db_path(path: Path | str) -> None:
    """Set a custom database path (useful for testing)."""
    global _DB_PATH, _engine
    _DB_PATH = Path(path)
    _engine = None  # Reset engine when path changes


def get_engine():
    """Get SQLAlchemy engine for SQLModel operations.

    Supports both SQLite and PostgreSQL based on DATABASE_URL.
    """
    global _engine
    if _engine is None:
        database_url = get_database_url()

        # SQLite-specific connection args
        connect_args = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        _engine = create_engine(database_url, echo=False, connect_args=connect_args)
    return _engine


def reset_engine() -> None:
    """Reset the engine (useful for testing or reconfiguration)."""
    global _engine
    _engine = None


def is_postgres() -> bool:
    """Check if using PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL", "")
    return database_url.startswith("postgres")


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel session for dependency injection."""
    with Session(get_engine()) as session:
        yield session


def init_sqlmodel_tables() -> None:
    """Create SQLModel tables (for services using SQLModel ORM)."""
    SQLModel.metadata.create_all(get_engine())
