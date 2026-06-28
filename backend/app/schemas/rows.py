"""Request/response schemas for the rows endpoint."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.upload import ColumnInfo


class RowsResponse(BaseModel):
    dataset_id: int
    page: int
    page_size: int
    total: int
    total_pages: int
    columns: list[ColumnInfo]
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Row objects keyed by column name (values are stored as text).",
    )
