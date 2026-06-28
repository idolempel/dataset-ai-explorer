"""Tests for POST /upload."""
from __future__ import annotations

import io


def _post_csv(client, content: bytes, filename: str = "employees.csv"):
    return client.post(
        "/upload",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
    )


def test_upload_success(client, employees_csv_bytes):
    resp = _post_csv(client, employees_csv_bytes)
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["dataset_id"] >= 1
    assert body["original_filename"] == "employees.csv"
    assert body["row_count"] == 5
    assert body["table_name"].startswith("ds_employees_")

    cols = {c["name"]: c["type"] for c in body["columns"]}
    assert cols["id"] == "integer"
    assert cols["name"] == "text"
    assert cols["department"] == "text"
    assert cols["salary"] == "integer"
    assert cols["is_manager"] == "boolean"
    assert cols["hired_at"] == "date"


def test_upload_rejects_non_csv(client):
    resp = client.post(
        "/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "csv" in resp.json()["detail"].lower()


def test_upload_rejects_empty_file(client):
    resp = _post_csv(client, b"")
    assert resp.status_code == 400


def test_upload_rejects_header_only(client):
    resp = _post_csv(client, b"id,name\n")
    assert resp.status_code == 422


def test_upload_handles_duplicate_and_messy_headers(client):
    content = b"First Name,First Name,123bad,\n" b"a,b,c,d\n"
    resp = _post_csv(client, content, filename="messy.csv")
    assert resp.status_code == 201, resp.text
    names = [c["name"] for c in resp.json()["columns"]]
    # Sanitized, de-duplicated, leading-digit fixed, empty -> fallback.
    assert names[0] == "first_name"
    assert names[1] == "first_name_2"
    assert names[2] == "bad"  # leading digits stripped
    assert names[3].startswith("col_")
    assert len(set(names)) == len(names)


def test_two_uploads_create_distinct_tables(client, employees_csv_bytes):
    r1 = _post_csv(client, employees_csv_bytes)
    r2 = _post_csv(client, employees_csv_bytes)
    assert r1.json()["table_name"] != r2.json()["table_name"]
    assert r1.json()["dataset_id"] != r2.json()["dataset_id"]
