"""POST /ask — answer a free-text question about a dataset via Claude (NL → SQL)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.database import get_db
from app.routers.deps import require_dataset
from app.schemas.ask import AskRequest, AskResponse
from app.services import llm_service

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> AskResponse:
    record = require_dataset(conn, payload.dataset_id)
    result = llm_service.ask(conn, record, payload.question)
    return AskResponse(
        question=result.question,
        answer=result.answer,
        generated_sql=result.generated_sql,
        result_preview=result.result_preview,
        row_count=result.row_count,
    )
