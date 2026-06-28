"""Claude-backed natural-language → SQL → answer pipeline.

Flow for ``POST /ask``:
1. Build a compact schema description for the target dataset.
2. Ask Claude to produce a single read-only SQLite ``SELECT`` (NL → SQL).
3. Validate/limit the SQL via :mod:`app.core.sql_guard` and execute it read-only.
4. Ask Claude to summarize the result rows into a concise natural-language answer.

The raw Anthropic call is isolated in :func:`_complete` so it is trivial to mock in
tests without hitting the network.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from app.config import get_settings
from app.core import sql_guard
from app.core.exceptions import AppError, BadRequestError
from app.models.dataset import DatasetRecord
from app.services.table_manager import quote_identifier

_MAX_SUMMARY_ROWS = 50  # rows fed back to the LLM for summarization


class LLMConfigError(AppError):
    status_code = 503


@dataclass
class AskResult:
    question: str
    answer: str
    generated_sql: str
    result_preview: list[dict[str, object]]
    row_count: int


# --- Anthropic client (lazy, isolated for testability) ---------------------

def _get_client():
    """Construct an Anthropic client from settings, or raise if unconfigured."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LLMConfigError("ANTHROPIC_API_KEY is not configured on the server.")
    # Imported lazily so the package is only required when /ask is used.
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _complete(system: str, user: str, *, max_tokens: int = 1024) -> str:
    """Single-turn completion; returns the assistant's text content."""
    client = _get_client()
    settings = get_settings()
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    return "".join(parts).strip()


# --- Prompt construction ----------------------------------------------------

def build_schema_description(record: DatasetRecord) -> str:
    """Render a compact schema string for the prompt context."""
    cols = ", ".join(f"{c['name']} ({c['type']})" for c in record.columns)
    return (
        f'Table name: "{record.table_name}"\n'
        f"Row count: {record.row_count}\n"
        f"Columns (name and inferred logical type): {cols}\n"
        "Note: all values are stored as TEXT in SQLite; cast where appropriate "
        "(e.g. CAST(col AS REAL)) for numeric aggregation."
    )


_SQL_SYSTEM = (
    "You are a careful data analyst that writes SQLite SQL. "
    "Given a table schema and a user question, respond with a SINGLE read-only "
    "SELECT statement that answers it. "
    "Rules: use only the provided table and columns; never modify data; do not use "
    "multiple statements; do not include explanations or Markdown — output ONLY the "
    "SQL statement."
)


def _build_sql_prompt(schema: str, question: str) -> str:
    return (
        f"{schema}\n\n"
        f"User question: {question}\n\n"
        "Return only the SQLite SELECT statement."
    )


_SUMMARY_SYSTEM = (
    "You are a helpful data analyst. Given a user's question, the SQL that was run, "
    "and the JSON result rows, write a concise, accurate answer for the user.\n"
    "Style rules:\n"
    "- Write in clean, plain English prose, friendly and easy to read.\n"
    "- Do NOT use any Markdown syntax: no headings (e.g. '#', '##'), no bold or "
    "italic markers (e.g. '**' or '__' or '*'), no bullet/numbered list markup, "
    "no code fences or backticks, and no Markdown tables.\n"
    "- If you need to list items, write them as a short natural sentence or "
    "separate them with commas; do not use dashes or asterisks as bullets.\n"
    "- Preserve the useful quantitative details from the results, such as averages, "
    "counts, minimums, maximums, totals, and comparisons, and reference concrete "
    "numbers.\n"
    "- Emojis are allowed but use them sparingly, and only when they naturally "
    "improve readability.\n"
    "- If the result is empty, say so plainly.\n"
    "Output only the plain-text answer."
)


def _build_summary_prompt(
    question: str, sql: str, rows: list[dict[str, object]]
) -> str:
    preview = rows[:_MAX_SUMMARY_ROWS]
    return (
        f"Question: {question}\n\n"
        f"SQL executed:\n{sql}\n\n"
        f"Result rows (JSON, up to {_MAX_SUMMARY_ROWS} shown):\n"
        f"{json.dumps(preview, default=str)}\n\n"
        "Write the answer for the user."
    )


# --- SQL execution (read-only) ---------------------------------------------

def _execute_select(conn: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        raise BadRequestError(f"Failed to execute generated SQL: {exc}") from exc
    return [dict(r) for r in rows]


def _table_referenced(sql: str, table_name: str) -> bool:
    """Best-effort check that the SQL references the dataset's table only."""
    lowered = sql.lower()
    return table_name.lower() in lowered or quote_identifier(table_name).lower() in lowered


# --- Public entrypoint ------------------------------------------------------

def ask(
    conn: sqlite3.Connection,
    record: DatasetRecord,
    question: str,
) -> AskResult:
    """Run the full NL → SQL → answer pipeline for one question."""
    if not question or not question.strip():
        raise BadRequestError("Question must not be empty.")

    settings = get_settings()
    schema = build_schema_description(record)

    raw_sql = _complete(_SQL_SYSTEM, _build_sql_prompt(schema, question), max_tokens=512)
    safe_sql = sql_guard.sanitize_and_validate(raw_sql, settings.max_llm_result_rows)

    if not _table_referenced(safe_sql, record.table_name):
        raise BadRequestError(
            "Generated SQL did not reference the dataset table; refusing to execute."
        )

    rows = _execute_select(conn, safe_sql)

    answer = _complete(
        _SUMMARY_SYSTEM,
        _build_summary_prompt(question, safe_sql, rows),
        max_tokens=1024,
    )

    return AskResult(
        question=question,
        answer=answer,
        generated_sql=safe_sql,
        result_preview=rows[:_MAX_SUMMARY_ROWS],
        row_count=len(rows),
    )
