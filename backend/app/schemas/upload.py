"""Request/response schemas for the upload endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    name: str = Field(..., description="Sanitized column name as stored in SQLite.")
    type: str = Field(..., description="Inferred logical type (integer/float/date/boolean/text).")


class UploadResponse(BaseModel):
    dataset_id: int
    table_name: str
    original_filename: str
    row_count: int
    columns: list[ColumnInfo]
