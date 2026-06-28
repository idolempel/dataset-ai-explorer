"""Tests for the LLM SQL safety guard."""
from __future__ import annotations

import pytest

from app.core.exceptions import BadRequestError
from app.core.sql_guard import sanitize_and_validate

MAX = 200


def test_select_passes_and_gets_limit():
    out = sanitize_and_validate("SELECT * FROM t", MAX)
    assert out == "SELECT * FROM t LIMIT 200"


def test_existing_small_limit_preserved():
    out = sanitize_and_validate("SELECT * FROM t LIMIT 5", MAX)
    assert out == "SELECT * FROM t LIMIT 5"


def test_large_limit_is_capped():
    out = sanitize_and_validate("SELECT * FROM t LIMIT 100000", MAX)
    assert out == "SELECT * FROM t LIMIT 200"


def test_cte_with_select_allowed():
    out = sanitize_and_validate("WITH x AS (SELECT 1 AS a) SELECT * FROM x", MAX)
    assert out.startswith("WITH x AS")
    assert out.endswith("LIMIT 200")


def test_code_fences_stripped():
    out = sanitize_and_validate("```sql\nSELECT 1\n```", MAX)
    assert out == "SELECT 1 LIMIT 200"


def test_comments_stripped():
    out = sanitize_and_validate("SELECT 1 -- sneaky\n", MAX)
    assert out == "SELECT 1 LIMIT 200"


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM t",
        "DROP TABLE t",
        "UPDATE t SET a = 1",
        "INSERT INTO t VALUES (1)",
        "ALTER TABLE t ADD COLUMN x",
        "PRAGMA table_info(t)",
        "ATTACH DATABASE 'x' AS y",
        "CREATE TABLE z (a INT)",
    ],
)
def test_non_select_rejected(sql):
    with pytest.raises(BadRequestError):
        sanitize_and_validate(sql, MAX)


def test_multiple_statements_rejected():
    with pytest.raises(BadRequestError):
        sanitize_and_validate("SELECT 1; DROP TABLE t", MAX)


def test_select_with_embedded_forbidden_keyword_rejected():
    # A SELECT that still tries to sneak a DML keyword (e.g. via a subquery trick).
    with pytest.raises(BadRequestError):
        sanitize_and_validate("SELECT 1 WHERE 1=1; DELETE FROM t", MAX)


def test_empty_rejected():
    with pytest.raises(BadRequestError):
        sanitize_and_validate("   ", MAX)
