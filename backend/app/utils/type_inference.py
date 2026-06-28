"""Lightweight logical-type inference for CSV columns.

SQLite is dynamically typed, so all values are stored as TEXT. We infer a *logical*
type per column (integer, float, boolean, date, text) from a sample of non-null
values. These logical types power frontend filtering and the LLM schema context.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

# Logical type constants
TYPE_INTEGER = "integer"
TYPE_FLOAT = "float"
TYPE_BOOLEAN = "boolean"
TYPE_DATE = "date"
TYPE_TEXT = "text"

LOGICAL_TYPES = {TYPE_INTEGER, TYPE_FLOAT, TYPE_BOOLEAN, TYPE_DATE, TYPE_TEXT}

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
_BOOL_VALUES = {"true", "false", "yes", "no", "t", "f", "y", "n", "0", "1"}
# Common ISO-ish date / datetime patterns
_DATE_RES = (
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?"),
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
)

_NULLISH = {"", "na", "n/a", "null", "none", "nan"}


def _is_null(value: str) -> bool:
    return value.strip().lower() in _NULLISH


def _matches_date(value: str) -> bool:
    return any(rx.match(value) for rx in _DATE_RES)


def infer_column_type(values: Iterable[object]) -> str:
    """Infer a single logical type from an iterable of raw cell values.

    Empty / null-like values are ignored. If a column has no usable samples, it
    defaults to ``text``. The inference is conservative: every non-null sample must
    match a candidate type for that type to be chosen, checked from most specific
    (boolean) to least specific (text).
    """
    samples = [str(v).strip() for v in values if v is not None and not _is_null(str(v))]
    if not samples:
        return TYPE_TEXT

    if all(s.lower() in _BOOL_VALUES for s in samples) and _looks_boolean(samples):
        return TYPE_BOOLEAN
    if all(_INT_RE.match(s) for s in samples):
        return TYPE_INTEGER
    if all(_FLOAT_RE.match(s) for s in samples):
        return TYPE_FLOAT
    if all(_matches_date(s) for s in samples):
        return TYPE_DATE
    return TYPE_TEXT


def _looks_boolean(samples: list[str]) -> bool:
    """Avoid classifying pure 0/1 integer columns as boolean unless textual booleans
    (true/false/yes/no/t/f/y/n) actually appear."""
    textual = {"true", "false", "yes", "no", "t", "f", "y", "n"}
    return any(s.lower() in textual for s in samples)


def infer_schema(
    rows: list[dict[str, object]],
    columns: list[str],
    sample_size: int = 200,
) -> dict[str, str]:
    """Infer logical types for each column given a list of row dicts."""
    sample = rows[:sample_size]
    schema: dict[str, str] = {}
    for col in columns:
        schema[col] = infer_column_type(row.get(col) for row in sample)
    return schema
