"""Unit tests for the typed sort expression helper."""
from __future__ import annotations

import io

from app.services.query_builder import _sort_expression
from app.utils.type_inference import (
    TYPE_BOOLEAN,
    TYPE_DATE,
    TYPE_FLOAT,
    TYPE_INTEGER,
    TYPE_TEXT,
)


def test_sort_expression_integer():
    assert _sort_expression("qty", TYPE_INTEGER) == 'CAST("qty" AS INTEGER)'


def test_sort_expression_float():
    assert _sort_expression("score", TYPE_FLOAT) == 'CAST("score" AS REAL)'


def test_sort_expression_text_boolean_date_are_plain():
    assert _sort_expression("label", TYPE_TEXT) == '"label"'
    assert _sort_expression("active", TYPE_BOOLEAN) == '"active"'
    assert _sort_expression("hired_at", TYPE_DATE) == '"hired_at"'


def test_sort_expression_unknown_type_defaults_to_plain():
    # Missing/unknown metadata -> safe text sort, no CAST.
    assert _sort_expression("x", None) == '"x"'


def test_sort_expression_quotes_identifier():
    # Embedded quotes are escaped via quote_identifier.
    assert _sort_expression('we"ird', TYPE_INTEGER) == 'CAST("we""ird" AS INTEGER)'


def test_numeric_sort_with_nulls_does_not_crash_and_pushes_empty_last(client):
    content = (
        (
            __import__("pathlib").Path(__file__).parent
            / "sample_data"
            / "numbers_with_nulls.csv"
        )
        .read_bytes()
    )
    up = client.post(
        "/upload",
        files={"file": ("numbers_with_nulls.csv", io.BytesIO(content), "text/csv")},
    )
    assert up.status_code == 201, up.text
    ds_id = up.json()["dataset_id"]
    assert {c["name"]: c["type"] for c in up.json()["columns"]}["qty"] == "integer"

    resp = client.get(
        "/rows",
        params={"dataset_id": ds_id, "sort_by": "qty", "sort_dir": "asc", "page_size": 100},
    )
    assert resp.status_code == 200, resp.text
    qtys = [r["qty"] for r in resp.json()["rows"]]

    # Empty value sorts last; the rest are numerically ascending (2, 10, 100).
    assert qtys[-1] in ("", None)
    non_empty = [q for q in qtys if q not in ("", None)]
    assert non_empty == ["2", "10", "100"]
