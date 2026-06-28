"""Request/response schemas for the ask endpoint."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    dataset_id: int = Field(..., ge=1)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    question: str
    answer: str
    generated_sql: str
    result_preview: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int
