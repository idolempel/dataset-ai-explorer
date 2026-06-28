"""Data-access helpers for the `datasets` metadata table.

Each uploaded CSV produces one row here plus a dedicated dynamic data table.
``columns_json`` stores an ordered list of ``{"name": ..., "type": ...}`` describing
the user-facing columns and their inferred logical types.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass
class DatasetRecord:
    id: int
    table_name: str
    original_filename: str
    row_count: int
    columns: list[dict[str, str]]
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "DatasetRecord":
        return cls(
            id=row["id"],
            table_name=row["table_name"],
            original_filename=row["original_filename"],
            row_count=row["row_count"],
            columns=json.loads(row["columns_json"]),
            created_at=row["created_at"],
        )


def create_dataset(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    original_filename: str,
    row_count: int,
    columns: list[dict[str, str]],
) -> DatasetRecord:
    cur = conn.execute(
        """
        INSERT INTO datasets (table_name, original_filename, row_count, columns_json)
        VALUES (?, ?, ?, ?)
        """,
        (table_name, original_filename, row_count, json.dumps(columns)),
    )
    dataset_id = int(cur.lastrowid)
    return get_dataset(conn, dataset_id)  # type: ignore[return-value]


def get_dataset(conn: sqlite3.Connection, dataset_id: int) -> DatasetRecord | None:
    row = conn.execute(
        "SELECT * FROM datasets WHERE id = ?",
        (dataset_id,),
    ).fetchone()
    return DatasetRecord.from_row(row) if row else None


def list_datasets(conn: sqlite3.Connection) -> list[DatasetRecord]:
    rows = conn.execute(
        "SELECT * FROM datasets ORDER BY created_at DESC, id DESC"
    ).fetchall()
    return [DatasetRecord.from_row(r) for r in rows]
