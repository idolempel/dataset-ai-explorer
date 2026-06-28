"""GET /datasets and GET /datasets/{id}/schema — helper endpoints for the UI."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import dataset as dataset_model
from app.routers.deps import require_dataset
from app.schemas.dataset import (
    DatasetListResponse,
    DatasetSchemaResponse,
    DatasetSummary,
)
from app.schemas.upload import ColumnInfo

router = APIRouter(tags=["datasets"])


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(conn: sqlite3.Connection = Depends(get_db)) -> DatasetListResponse:
    records = dataset_model.list_datasets(conn)
    return DatasetListResponse(
        datasets=[
            DatasetSummary(
                dataset_id=r.id,
                table_name=r.table_name,
                original_filename=r.original_filename,
                row_count=r.row_count,
                created_at=r.created_at,
            )
            for r in records
        ]
    )


@router.get("/datasets/{dataset_id}/schema", response_model=DatasetSchemaResponse)
def get_dataset_schema(
    dataset_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> DatasetSchemaResponse:
    record = require_dataset(conn, dataset_id)
    return DatasetSchemaResponse(
        dataset_id=record.id,
        table_name=record.table_name,
        original_filename=record.original_filename,
        row_count=record.row_count,
        columns=[ColumnInfo(**c) for c in record.columns],
    )
