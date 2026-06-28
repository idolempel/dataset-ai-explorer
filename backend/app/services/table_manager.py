"""Safe creation, introspection, and naming of dynamic data tables.

All user-derived identifiers (table names, column names) are sanitized and quoted to
avoid SQL injection via DDL. Reserved/empty names are handled deterministically.
"""
from __future__ import annotations

import re
import secrets
import sqlite3

from app.core.exceptions import BadRequestError

# Identifiers that must never be used as a generated data table name.
_RESERVED_TABLES = {"datasets", "sqlite_master", "sqlite_sequence"}

_IDENT_CLEAN_RE = re.compile(r"[^0-9a-zA-Z_]+")
_LEADING_NON_ALPHA_RE = re.compile(r"^[^a-zA-Z_]+")

MAX_IDENT_LEN = 60


def sanitize_identifier(raw: str, fallback: str) -> str:
    """Turn an arbitrary string into a safe SQLite identifier (snake-ish).

    - Lowercased, non-alphanumeric runs collapsed to ``_``.
    - Stripped of leading characters that are not a letter/underscore.
    - Truncated to a reasonable length.
    - Falls back to ``fallback`` when nothing usable remains.
    """
    cleaned = _IDENT_CLEAN_RE.sub("_", raw.strip().lower())
    cleaned = _LEADING_NON_ALPHA_RE.sub("", cleaned)
    cleaned = cleaned.strip("_")
    cleaned = cleaned[:MAX_IDENT_LEN]
    if not cleaned:
        cleaned = fallback
    return cleaned


def quote_identifier(identifier: str) -> str:
    """Quote an identifier for safe inclusion in SQL (double-quote escaped)."""
    return '"' + identifier.replace('"', '""') + '"'


def sanitize_columns(raw_columns: list[str]) -> list[str]:
    """Sanitize and de-duplicate a list of column names, preserving order."""
    if not raw_columns:
        raise BadRequestError("CSV has no columns.")

    result: list[str] = []
    seen: set[str] = set()
    for idx, raw in enumerate(raw_columns):
        name = sanitize_identifier(raw, fallback=f"col_{idx + 1}")
        base = name
        suffix = 1
        while name in seen:
            suffix += 1
            name = f"{base}_{suffix}"
        seen.add(name)
        result.append(name)
    return result


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def generate_table_name(conn: sqlite3.Connection, original_filename: str) -> str:
    """Generate a unique, safe data table name from the uploaded filename."""
    stem = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
    base = sanitize_identifier(stem, fallback="dataset")
    for _ in range(20):
        candidate = f"ds_{base}_{secrets.token_hex(3)}"[: MAX_IDENT_LEN + 3]
        if candidate in _RESERVED_TABLES:
            continue
        if not table_exists(conn, candidate):
            return candidate
    raise BadRequestError("Could not generate a unique table name; please retry.")


def create_data_table(
    conn: sqlite3.Connection,
    table_name: str,
    columns: list[str],
) -> None:
    """Create a data table with an internal rowid PK plus all columns as TEXT.

    Values are stored as TEXT; logical types live in the dataset metadata.
    """
    col_defs = ", ".join(f"{quote_identifier(c)} TEXT" for c in columns)
    ddl = (
        f"CREATE TABLE {quote_identifier(table_name)} "
        f"(__row_id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})"
    )
    conn.execute(ddl)


def insert_rows(
    conn: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    rows: list[dict[str, object]],
) -> int:
    """Bulk-insert rows (as text) into the data table. Returns inserted count."""
    if not rows:
        return 0
    placeholders = ", ".join("?" for _ in columns)
    col_sql = ", ".join(quote_identifier(c) for c in columns)
    sql = f"INSERT INTO {quote_identifier(table_name)} ({col_sql}) VALUES ({placeholders})"

    def to_value(v: object) -> object:
        if v is None:
            return None
        return str(v)

    payload = [tuple(to_value(row.get(c)) for c in columns) for row in rows]
    conn.executemany(sql, payload)
    return len(payload)


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """Return the user-facing columns of a data table (excludes __row_id)."""
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()
    return [r["name"] for r in rows if r["name"] != "__row_id"]
