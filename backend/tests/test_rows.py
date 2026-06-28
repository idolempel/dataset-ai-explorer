"""Tests for GET /rows."""
from __future__ import annotations


def test_rows_basic_pagination(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get("/rows", params={"dataset_id": ds_id, "page": 1, "page_size": 2})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["dataset_id"] == ds_id
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_pages"] == 3
    assert len(body["rows"]) == 2
    assert {c["name"] for c in body["columns"]} == {
        "id", "name", "department", "salary", "is_manager", "hired_at"
    }


def test_rows_second_page(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get("/rows", params={"dataset_id": ds_id, "page": 3, "page_size": 2})
    body = resp.json()
    assert len(body["rows"]) == 1  # 5 rows, last page has 1


def test_rows_global_search(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get("/rows", params={"dataset_id": ds_id, "search": "Research"})
    body = resp.json()
    assert body["total"] == 2
    assert all(r["department"] == "Research" for r in body["rows"])


def test_rows_column_filter(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get(
        "/rows",
        params={"dataset_id": ds_id, "filter.department": "Engineering"},
    )
    body = resp.json()
    assert body["total"] == 3
    assert all(r["department"] == "Engineering" for r in body["rows"])


def test_rows_sorting(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get(
        "/rows",
        params={"dataset_id": ds_id, "sort_by": "name", "sort_dir": "asc"},
    )
    names = [r["name"] for r in resp.json()["rows"]]
    assert names == sorted(names)


def test_rows_invalid_sort_column(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get("/rows", params={"dataset_id": ds_id, "sort_by": "nope"})
    assert resp.status_code == 400
    assert "sort column" in resp.json()["detail"].lower()


def test_rows_unknown_filter_column(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get("/rows", params={"dataset_id": ds_id, "filter.bogus": "x"})
    assert resp.status_code == 400
    assert "filter column" in resp.json()["detail"].lower()


def test_rows_page_size_cap(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    resp = client.get("/rows", params={"dataset_id": ds_id, "page_size": 9999})
    # FastAPI Query(le=MAX_PAGE_SIZE) rejects with 422.
    assert resp.status_code == 422


def test_rows_dataset_not_found(client):
    resp = client.get("/rows", params={"dataset_id": 999})
    assert resp.status_code == 404


def test_rows_like_wildcards_are_literal(client, uploaded_dataset):
    ds_id = uploaded_dataset["dataset_id"]
    # '%' should be treated literally and match nothing in the sample data.
    resp = client.get("/rows", params={"dataset_id": ds_id, "search": "%"})
    assert resp.json()["total"] == 0


# --- Typed sorting -----------------------------------------------------------


def _sorted_column(client, ds_id, column, direction="asc"):
    resp = client.get(
        "/rows",
        params={
            "dataset_id": ds_id,
            "sort_by": column,
            "sort_dir": direction,
            "page_size": 100,
        },
    )
    assert resp.status_code == 200, resp.text
    return [r[column] for r in resp.json()["rows"]]


def test_numbers_dataset_inferred_types(numbers_dataset):
    types = {c["name"]: c["type"] for c in numbers_dataset["columns"]}
    assert types["qty"] == "integer"
    assert types["score"] == "float"
    assert types["active"] == "boolean"
    assert types["label"] == "text"


def test_integer_sort_is_numeric_not_lexicographic(client, numbers_dataset):
    ds_id = numbers_dataset["dataset_id"]
    asc = _sorted_column(client, ds_id, "qty", "asc")
    # Numeric order is 2, 10, 100 — NOT lexicographic ("10","100","2").
    assert asc == ["2", "10", "100"]

    desc = _sorted_column(client, ds_id, "qty", "desc")
    assert desc == ["100", "10", "2"]


def test_float_sort_is_numeric(client, numbers_dataset):
    ds_id = numbers_dataset["dataset_id"]
    asc = _sorted_column(client, ds_id, "score", "asc")
    # Numeric float order: 2.5, 10.1, 100.0 (lexicographic would be 10.1,100.0,2.5).
    assert asc == ["2.5", "10.1", "100.0"]


def test_text_sort_still_works(client, numbers_dataset):
    ds_id = numbers_dataset["dataset_id"]
    asc = _sorted_column(client, ds_id, "label", "asc")
    assert asc == ["a", "b", "c"]


def test_boolean_sort_is_deterministic_text(client, numbers_dataset):
    ds_id = numbers_dataset["dataset_id"]
    asc = _sorted_column(client, ds_id, "active", "asc")
    # Only "true"/"false" values -> lexicographic is deterministic: false < true.
    assert asc == ["false", "true", "true"]


def test_employees_salary_sorts_numerically(client, uploaded_dataset):
    # salary is inferred as integer; ensure ascending order is numeric.
    ds_id = uploaded_dataset["dataset_id"]
    asc = _sorted_column(client, ds_id, "salary", "asc")
    as_ints = [int(v) for v in asc]
    assert as_ints == sorted(as_ints)
