"""Shared pytest fixtures: isolated temp DB + FastAPI TestClient."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SAMPLE_DIR = Path(__file__).parent / "sample_data"


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """A TestClient backed by a throwaway SQLite database per test."""
    # Point the app at an isolated DB file before settings are cached.
    db_file = tmp_path / "test_app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Reset cached settings so the env override above takes effect.
    from app.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()


@pytest.fixture()
def employees_csv_bytes() -> bytes:
    return (SAMPLE_DIR / "employees.csv").read_bytes()


@pytest.fixture()
def uploaded_dataset(client, employees_csv_bytes) -> dict:
    """Upload the sample CSV and return the parsed UploadResponse body."""
    import io

    resp = client.post(
        "/upload",
        files={"file": ("employees.csv", io.BytesIO(employees_csv_bytes), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def numbers_csv_bytes() -> bytes:
    return (SAMPLE_DIR / "numbers.csv").read_bytes()


@pytest.fixture()
def numbers_dataset(client, numbers_csv_bytes) -> dict:
    """Upload a numeric-focused CSV (qty=int, score=float) for sort tests."""
    import io

    resp = client.post(
        "/upload",
        files={"file": ("numbers.csv", io.BytesIO(numbers_csv_bytes), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
