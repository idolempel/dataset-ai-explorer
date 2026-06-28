"""POST /upload — accept a CSV and create a dynamic SQLite table."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, File, UploadFile

from app.config import get_settings
from app.core.exceptions import BadRequestError
from app.database import get_db
from app.schemas.upload import ColumnInfo, UploadResponse
from app.services import csv_ingest

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db),
) -> UploadResponse:
    settings = get_settings()

    filename = file.filename or "dataset.csv"
    if not filename.lower().endswith(".csv"):
        raise BadRequestError("Only .csv files are supported.")

    content = await file.read()
    if not content:
        raise BadRequestError("Uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise BadRequestError(
            f"File exceeds maximum allowed size of {settings.max_upload_bytes} bytes."
        )

    record = csv_ingest.ingest_csv(conn, content=content, original_filename=filename)

    return UploadResponse(
        dataset_id=record.id,
        table_name=record.table_name,
        original_filename=record.original_filename,
        row_count=record.row_count,
        columns=[ColumnInfo(**c) for c in record.columns],
    )
