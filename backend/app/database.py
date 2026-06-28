"""SQLite connection management and metadata schema bootstrap.

We use the standard-library ``sqlite3`` module directly (rather than an ORM) because
this app creates tables dynamically from uploaded CSVs, which is far more transparent
with raw DDL.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings


def _resolve_db_path() -> Path:
    settings = get_settings()
    db_path = settings.database_file
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with sensible defaults.

    Caller is responsible for closing the connection (use :func:`connection` for an
    automatically managed context).
    """
    db_path = _resolve_db_path()
    # check_same_thread=False: each request creates and fully manages its own
    # connection; Starlette's TestClient (and the async portal) may run the
    # endpoint on a different thread than the one that created the connection.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection and committing/closing on exit."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# FastAPI dependency
def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency that yields a managed connection."""
    with connection() as conn:
        yield conn


# --- Metadata schema -------------------------------------------------------

DATASETS_DDL = """
CREATE TABLE IF NOT EXISTS datasets (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name        TEXT    NOT NULL UNIQUE,
    original_filename TEXT    NOT NULL,
    row_count         INTEGER NOT NULL DEFAULT 0,
    columns_json      TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    """Create metadata tables if they do not exist."""
    with connection() as conn:
        conn.execute(DATASETS_DDL)
