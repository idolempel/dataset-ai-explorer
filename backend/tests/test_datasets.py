"""Tests for GET /datasets and GET /datasets/{id}/schema."""
from __future__ import annotations


def test_list_datasets(client, uploaded_dataset):
    resp = client.get("/datasets")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["datasets"]) == 1
    item = body["datasets"][0]
    assert item["dataset_id"] == uploaded_dataset["dataset_id"]
    assert item["original_filename"] == "employees.csv"
    assert item["row_count"] == 5


def test_list_datasets_empty(client):
    resp = client.get("/datasets")
    assert resp.status_code == 200
    assert resp.json()["datasets"] == []


def test_dataset_schema(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get(f"/datasets/{ds_id}/schema")
    assert resp.status_code == 200
    body = resp.json()
    cols = {c["name"]: c["type"] for c in body["columns"]}
    assert cols["salary"] == "integer"
    assert cols["hired_at"] == "date"
    assert cols["is_manager"] == "boolean"


def test_dataset_schema_not_found(client):
    resp = client.get("/datasets/999/schema")
    assert resp.status_code == 404
