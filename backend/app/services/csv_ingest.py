"""CSV ingestion: parse bytes, infer types, create + populate a dynamic table."""
from __future__ import annotations

import csv
import io
import sqlite3

from app.core.exceptions import BadRequestError, UnprocessableError
from app.models import dataset as dataset_model
from app.models.dataset import DatasetRecord
from app.services import table_manager
from app.utils import type_inference


def _decode(content: bytes) -> str:
    """Decode uploaded bytes, tolerating a UTF-8 BOM and falling back to latin-1."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise BadRequestError("Unable to decode file; expected a UTF-8 or Latin-1 CSV.")


def parse_csv(content: bytes) -> tuple[list[str], list[dict[str, object]]]:
    """Parse CSV bytes into (header, rows) using the stdlib csv module.

    Raises :class:`BadRequestError` for empty files or files without a header.
    """
    text = _decode(content)
    if not text.strip():
        raise BadRequestError("Uploaded CSV is empty.")

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise BadRequestError("Uploaded CSV has no header row.") from None

    header = [h.strip() for h in header]
    if not any(header):
        raise BadRequestError("CSV header row is empty.")

    raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    return header, _rows_to_dicts(header, raw_rows)


def _rows_to_dicts(
    header: list[str], raw_rows: list[list[str]]
) -> list[dict[str, object]]:
    """Zip raw row lists against the (raw) header, padding/truncating as needed."""
    width = len(header)
    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        if len(raw) < width:
            raw = raw + [None] * (width - len(raw))  # type: ignore[list-item]
        elif len(raw) > width:
            raw = raw[:width]
        rows.append({header[i]: raw[i] for i in range(width)})
    return rows


def ingest_csv(
    conn: sqlite3.Connection,
    *,
    content: bytes,
    original_filename: str,
) -> DatasetRecord:
    """Full ingestion pipeline. Returns the created :class:`DatasetRecord`.

    Steps: parse -> sanitize columns -> infer types -> create table -> insert rows ->
    register dataset metadata.
    """
    raw_header, raw_rows = parse_csv(content)
    if not raw_rows:
        raise UnprocessableError("CSV contains a header but no data rows.")

    safe_columns = table_manager.sanitize_columns(raw_header)

    # Map sanitized column names back over the parsed rows (keyed by raw header).
    raw_to_safe = dict(zip(raw_header, safe_columns, strict=True))
    normalized_rows: list[dict[str, object]] = [
        {raw_to_safe[k]: v for k, v in row.items()} for row in raw_rows
    ]

    inferred = type_inference.infer_schema(normalized_rows, safe_columns)
    columns_meta = [{"name": c, "type": inferred[c]} for c in safe_columns]

    table_name = table_manager.generate_table_name(conn, original_filename)
    table_manager.create_data_table(conn, table_name, safe_columns)
    inserted = table_manager.insert_rows(conn, table_name, safe_columns, normalized_rows)

    return dataset_model.create_dataset(
        conn,
        table_name=table_name,
        original_filename=original_filename,
        row_count=inserted,
        columns=columns_meta,
    )
