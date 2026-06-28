"""Unit tests for logical type inference."""
from __future__ import annotations

from app.utils import type_inference as ti


def test_integer_inference():
    assert ti.infer_column_type(["1", "2", "-3", "  4 "]) == ti.TYPE_INTEGER


def test_float_inference():
    assert ti.infer_column_type(["1.5", "2", "3.0e2"]) == ti.TYPE_FLOAT


def test_boolean_inference_requires_textual_booleans():
    assert ti.infer_column_type(["true", "false", "yes", "no"]) == ti.TYPE_BOOLEAN
    # Pure 0/1 should be integer, not boolean.
    assert ti.infer_column_type(["0", "1", "1", "0"]) == ti.TYPE_INTEGER


def test_date_inference():
    assert ti.infer_column_type(["2021-03-01", "2020-07-15"]) == ti.TYPE_DATE
    assert ti.infer_column_type(["01/02/2021"]) == ti.TYPE_DATE


def test_text_inference_and_nulls():
    assert ti.infer_column_type(["alpha", "beta"]) == ti.TYPE_TEXT
    # Null-ish only -> text fallback.
    assert ti.infer_column_type(["", "N/A", "null"]) == ti.TYPE_TEXT
    # Nulls ignored when other samples are integers.
    assert ti.infer_column_type(["", "5", "10"]) == ti.TYPE_INTEGER


def test_mixed_falls_back_to_text():
    assert ti.infer_column_type(["1", "abc", "2021-01-01"]) == ti.TYPE_TEXT
