"""Build safe, parameterized SELECT queries for paginated/filtered row access.

All column references are validated against the dataset's known column set before being
interpolated as quoted identifiers; all user *values* are passed as bound parameters.
This keeps the dynamic-table querying safe from SQL injection.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from app.core.exceptions import BadRequestError
from app.services.table_manager import quote_identifier
from app.utils.type_inference import TYPE_FLOAT, TYPE_INTEGER

# Pagination bounds
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200

SORT_DIRECTIONS = {"asc", "desc"}


@dataclass
class RowsQuery:
    """Validated inputs for a rows query.

    ``column_types`` maps each column name to its inferred logical type (from the
    trusted dataset metadata). It is used only to choose a typed ORDER BY expression
    so numeric columns sort numerically rather than lexicographically. It never
    contains user input.
    """

    table_name: str
    columns: list[str]
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    sort_by: str | None = None
    sort_dir: str = "asc"
    search: str | None = None
    filters: dict[str, str] = field(default_factory=dict)
    column_types: dict[str, str] = field(default_factory=dict)


@dataclass
class RowsResult:
    rows: list[dict[str, object]]
    total: int
    page: int
    page_size: int
    total_pages: int


def _validate(query: RowsQuery) -> None:
    valid = set(query.columns)

    if query.page < 1:
        raise BadRequestError("page must be >= 1.")
    if query.page_size < 1:
        raise BadRequestError("page_size must be >= 1.")
    if query.page_size > MAX_PAGE_SIZE:
        raise BadRequestError(f"page_size must be <= {MAX_PAGE_SIZE}.")

    if query.sort_by is not None and query.sort_by not in valid:
        raise BadRequestError(f"Unknown sort column: {query.sort_by!r}.")
    if query.sort_dir.lower() not in SORT_DIRECTIONS:
        raise BadRequestError("sort_dir must be 'asc' or 'desc'.")

    for col in query.filters:
        if col not in valid:
            raise BadRequestError(f"Unknown filter column: {col!r}.")


def _build_where(query: RowsQuery) -> tuple[str, list[object]]:
    """Build a WHERE clause and bound parameters from filters + global search."""
    clauses: list[str] = []
    params: list[object] = []

    # Per-column substring filters (case-insensitive LIKE).
    for col, value in query.filters.items():
        if value is None or value == "":
            continue
        clauses.append(f"{quote_identifier(col)} LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(value)}%")

    # Global search across all columns (OR of LIKE).
    if query.search:
        term = f"%{_escape_like(query.search)}%"
        ors = [f"{quote_identifier(c)} LIKE ? ESCAPE '\\'" for c in query.columns]
        if ors:
            clauses.append("(" + " OR ".join(ors) + ")")
            params.extend([term] * len(query.columns))

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is treated literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _sort_expression(column: str, column_type: str | None) -> str:
    """Build a typed ORDER BY key expression for a (validated) column.

    The ``column`` name has already been validated against the dataset's known
    columns and is quoted here. ``column_type`` comes only from trusted internal
    metadata, so it is safe to map it to a fixed CAST keyword.

    - integer -> CAST(col AS INTEGER)  (numeric, not lexicographic)
    - float   -> CAST(col AS REAL)     (numeric)
    - text / boolean / date -> plain text sort

    Empty strings and NULLs do not crash: SQLite casts ''/NULL without error. To
    keep them from being treated as 0 and interleaved with real zeros, callers add
    a leading "empties last" key (see :func:`execute_rows_query`).
    """
    qcol = quote_identifier(column)
    if column_type == TYPE_INTEGER:
        return f"CAST({qcol} AS INTEGER)"
    if column_type == TYPE_FLOAT:
        return f"CAST({qcol} AS REAL)"
    # boolean (true/false only), date, and text: deterministic text ordering.
    return qcol


def execute_rows_query(conn: sqlite3.Connection, query: RowsQuery) -> RowsResult:
    """Validate inputs, run the count + page queries, and return a RowsResult."""
    _validate(query)

    qtable = quote_identifier(query.table_name)
    where, params = _build_where(query)

    total = int(
        conn.execute(f"SELECT COUNT(*) AS c FROM {qtable}{where}", params).fetchone()["c"]
    )

    order = ""
    if query.sort_by:
        direction = query.sort_dir.upper()
        col_type = query.column_types.get(query.sort_by)
        sort_expr = _sort_expression(query.sort_by, col_type)
        qcol = quote_identifier(query.sort_by)
        # Push NULL/empty values to the end regardless of direction, then apply the
        # typed sort. This keeps empty cells from masquerading as 0 for numeric casts.
        empties_last = f"CASE WHEN {qcol} IS NULL OR {qcol} = '' THEN 1 ELSE 0 END"
        order = f" ORDER BY {empties_last} ASC, {sort_expr} {direction}"

    offset = (query.page - 1) * query.page_size
    select_cols = ", ".join(quote_identifier(c) for c in query.columns)
    sql = f"SELECT {select_cols} FROM {qtable}{where}{order} LIMIT ? OFFSET ?"
    page_params = [*params, query.page_size, offset]

    raw_rows = conn.execute(sql, page_params).fetchall()
    rows = [dict(r) for r in raw_rows]

    total_pages = (total + query.page_size - 1) // query.page_size if total else 0

    return RowsResult(
        rows=rows,
        total=total,
        page=query.page,
        page_size=query.page_size,
        total_pages=total_pages,
    )
