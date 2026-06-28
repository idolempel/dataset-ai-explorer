"""Shared router dependencies/helpers."""
from __future__ import annotations

import sqlite3

from app.core.exceptions import NotFoundError
from app.models import dataset as dataset_model
from app.models.dataset import DatasetRecord


def require_dataset(conn: sqlite3.Connection, dataset_id: int) -> DatasetRecord:
    """Return the dataset or raise a 404 NotFoundError."""
    record = dataset_model.get_dataset(conn, dataset_id)
    if record is None:
        raise NotFoundError(f"Dataset {dataset_id} not found.")
    return record
