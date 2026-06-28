"""Validation guardrails for LLM-generated SQL.

The ``/ask`` flow lets Claude generate SQL. Before executing anything, we enforce:

1. Exactly one statement (no ``;``-chaining).
2. Statement must be a read-only ``SELECT`` (or a ``WITH ... SELECT`` CTE).
3. No forbidden keywords (DDL/DML/PRAGMA/ATTACH/etc.).
4. A row ``LIMIT`` is enforced (added if missing, capped if too large).

This is defense-in-depth alongside executing on a read-only connection.
"""
from __future__ import annotations

import re

from app.core.exceptions import BadRequestError

# Keywords that must never appear (word-boundary matched, case-insensitive).
_FORBIDDEN = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
    "reindex",
    "grant",
    "revoke",
)

_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(_FORBIDDEN) + r")\b",
    re.IGNORECASE,
)

_LIMIT_RE = re.compile(r"\blimit\b\s+(\d+)", re.IGNORECASE)
_COMMENT_RE = re.compile(r"(--[^\n]*$)|(/\*.*?\*/)", re.MULTILINE | re.DOTALL)


def _strip_comments(sql: str) -> str:
    return _COMMENT_RE.sub("", sql).strip()


def _strip_code_fences(sql: str) -> str:
    """Remove Markdown code fences the LLM might wrap SQL in."""
    text = sql.strip()
    if text.startswith("```"):
        # Drop the opening fence line (``` or ```sql) and trailing fence.
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def sanitize_and_validate(sql: str, max_rows: int) -> str:
    """Return a safe, single-statement SELECT with an enforced LIMIT.

    Raises :class:`BadRequestError` if the SQL is unsafe or not a SELECT.
    """
    if not sql or not sql.strip():
        raise BadRequestError("Generated SQL was empty.")

    cleaned = _strip_code_fences(sql)
    cleaned = _strip_comments(cleaned)
    cleaned = cleaned.strip().rstrip(";").strip()

    if not cleaned:
        raise BadRequestError("Generated SQL was empty after sanitization.")

    # Single statement only.
    if ";" in cleaned:
        raise BadRequestError("Only a single SQL statement is allowed.")

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise BadRequestError("Only read-only SELECT queries are allowed.")

    if _FORBIDDEN_RE.search(cleaned):
        raise BadRequestError("Generated SQL contains a forbidden keyword.")

    return _enforce_limit(cleaned, max_rows)


def _enforce_limit(sql: str, max_rows: int) -> str:
    """Append a LIMIT if missing, or cap an existing one to ``max_rows``."""
    match = _LIMIT_RE.search(sql)
    if match:
        requested = int(match.group(1))
        if requested > max_rows:
            return _LIMIT_RE.sub(f"LIMIT {max_rows}", sql, count=1)
        return sql
    return f"{sql} LIMIT {max_rows}"
