"""Tests for POST /ask with the Claude client mocked.

We patch ``llm_service._complete`` so no network calls occur. The first call returns
the NL→SQL output; the second returns the natural-language summary.
"""
from __future__ import annotations

import pytest

from app.services import llm_service


class _FakeLLM:
    """Returns queued responses for successive _complete() calls."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts = []

    def __call__(self, system, user, *, max_tokens=1024):
        self.prompts.append((system, user))
        return self._responses.pop(0)


def _patch_llm(monkeypatch, responses):
    fake = _FakeLLM(responses)
    monkeypatch.setattr(llm_service, "_complete", fake)
    return fake


def test_ask_happy_path(client, uploaded_dataset, monkeypatch):
    ds_id = uploaded_dataset["dataset_id"]
    table = uploaded_dataset["table_name"]

    sql = f'SELECT department, COUNT(*) AS n FROM "{table}" GROUP BY department'
    summary = "Engineering has 3 employees and Research has 2."
    fake = _patch_llm(monkeypatch, [sql, summary])

    resp = client.post("/ask", json={"dataset_id": ds_id, "question": "Counts per dept?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["question"] == "Counts per dept?"
    assert body["answer"] == summary
    assert "GROUP BY department" in body["generated_sql"]
    assert body["generated_sql"].rstrip().endswith("LIMIT 200")
    assert body["row_count"] == 2
    # Two LLM calls: NL->SQL then summarize.
    assert len(fake.prompts) == 2


def test_ask_rejects_non_select_sql(client, uploaded_dataset, monkeypatch):
    ds_id = uploaded_dataset["dataset_id"]
    table = uploaded_dataset["table_name"]
    _patch_llm(monkeypatch, [f'DELETE FROM "{table}"', "should not be reached"])

    resp = client.post("/ask", json={"dataset_id": ds_id, "question": "delete stuff"})
    assert resp.status_code == 400
    assert "select" in resp.json()["detail"].lower()


def test_ask_rejects_sql_not_referencing_table(client, uploaded_dataset, monkeypatch):
    ds_id = uploaded_dataset["dataset_id"]
    _patch_llm(monkeypatch, ["SELECT 1 AS x", "unused"])

    resp = client.post("/ask", json={"dataset_id": ds_id, "question": "anything"})
    assert resp.status_code == 400
    assert "dataset table" in resp.json()["detail"].lower()


def test_ask_dataset_not_found(client, monkeypatch):
    _patch_llm(monkeypatch, ["SELECT 1", "unused"])
    resp = client.post("/ask", json={"dataset_id": 999, "question": "hi"})
    assert resp.status_code == 404


def test_ask_empty_question_rejected(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.post("/ask", json={"dataset_id": ds_id, "question": ""})
    # Pydantic min_length=1 -> 422.
    assert resp.status_code == 422


def test_ask_missing_api_key_returns_503(client, uploaded_dataset, monkeypatch):
    ds_id = uploaded_dataset["dataset_id"]

    # Force settings to report no API key.
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)

    resp = client.post("/ask", json={"dataset_id": ds_id, "question": "hi"})
    assert resp.status_code == 503


def test_build_schema_description_contains_columns(uploaded_dataset, client, monkeypatch):
    # Unit-level check on prompt context via the service helper.
    import sqlite3

    from app.database import get_connection
    from app.models import dataset as dataset_model

    conn: sqlite3.Connection = get_connection()
    try:
        record = dataset_model.get_dataset(conn, uploaded_dataset["dataset_id"])
    finally:
        conn.close()

    assert record is not None
    desc = llm_service.build_schema_description(record)
    assert record.table_name in desc
    assert "salary (integer)" in desc
