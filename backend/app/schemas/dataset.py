"""Response schemas for dataset listing / schema endpoints."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.upload import ColumnInfo


class DatasetSummary(BaseModel):
    dataset_id: int
    table_name: str
    original_filename: str
    row_count: int
    created_at: str


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class DatasetSchemaResponse(BaseModel):
    dataset_id: int
    table_name: str
    original_filename: str
    row_count: int
    columns: list[ColumnInfo]
