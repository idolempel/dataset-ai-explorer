"""GET /rows — paginated, filterable rows for a dataset.

Filtering:
- ``search``: global case-insensitive substring across all columns.
- ``filter.<column>=<value>``: per-column case-insensitive substring filter
  (column-specific filters are read from arbitrary query params prefixed with
  ``filter.``).
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Request

from app.database import get_db
from app.routers.deps import require_dataset
from app.schemas.rows import RowsResponse
from app.schemas.upload import ColumnInfo
from app.services import query_builder
from app.services.query_builder import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, RowsQuery

router = APIRouter(tags=["rows"])

_FILTER_PREFIX = "filter."


def _extract_filters(request: Request, valid_columns: set[str]) -> dict[str, str]:
    """Read ``filter.<column>`` query params into a {column: value} dict.

    Unknown columns are ignored here and validated downstream for a clear error.
    """
    filters: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith(_FILTER_PREFIX):
            col = key[len(_FILTER_PREFIX):]
            if col:
                filters[col] = value
    return filters


@router.get("/rows", response_model=RowsResponse)
def get_rows(
    request: Request,
    dataset_id: int = Query(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    search: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> RowsResponse:
    record = require_dataset(conn, dataset_id)
    column_names = [c["name"] for c in record.columns]
    # Trusted internal metadata: column name -> inferred logical type. Used only to
    # choose a typed ORDER BY expression (never derived from user input).
    column_types = {c["name"]: c["type"] for c in record.columns}

    filters = _extract_filters(request, set(column_names))

    query = RowsQuery(
        table_name=record.table_name,
        columns=column_names,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search=search,
        filters=filters,
        column_types=column_types,
    )
    result = query_builder.execute_rows_query(conn, query)

    return RowsResponse(
        dataset_id=dataset_id,
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
        columns=[ColumnInfo(**c) for c in record.columns],
        rows=result.rows,
    )
