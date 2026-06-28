# Full-Stack Dataset Explorer with AI Insights

Upload a CSV, explore it in a filterable/paginated table, and ask natural-language
questions answered by Anthropic Claude (NL → SQL → summarized answer).

## Tech Stack

- **Backend:** Python / FastAPI / SQLite (raw `sqlite3`, dynamic tables)
- **Frontend:** React (Vite)
- **LLM:** Anthropic Claude (`claude-sonnet-4-6`, configurable via env)

## Project Structure

```
Applied_Materials_Task_A/
├── backend/    # FastAPI app, SQLite, services, tests
└── frontend/   # React (Vite) SPA
```

## Backend — Setup & Run

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt

# Configure secrets
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# then edit .env and set ANTHROPIC_API_KEY

python run.py                # starts uvicorn on http://localhost:8000
```

Interactive API docs: http://localhost:8000/docs

### Run backend tests

```bash
cd backend
pytest -q
```

## API Endpoints

| Method | Path                      | Description                                   |
|--------|---------------------------|-----------------------------------------------|
| POST   | `/upload`                 | Upload a CSV; creates a dynamic SQLite table. |
| GET    | `/rows`                   | Paginated/filtered rows for a dataset.        |
| POST   | `/ask`                    | Ask a question (NL → SQL → answer).           |
| GET    | `/datasets`               | List uploaded datasets.                       |
| GET    | `/datasets/{id}/schema`   | Column schema for a dataset.                  |

## Design Decisions

- **Multi-dataset registry:** each upload creates its own data table plus a row in a
  `datasets` metadata table.
- **Dynamic typing:** values stored as `TEXT` in SQLite; inferred logical types
  (`integer`, `float`, `date`, `boolean`, `text`) are stored as metadata and used
  for filtering and LLM context.
- **`/ask` safety:** Claude generates a single read-only `SELECT`, validated by a SQL
  guard (SELECT-only, single statement, forced `LIMIT`, identifier checks) before
  execution; results are then summarized by Claude.
- **Secrets:** loaded from environment via `pydantic-settings`; never hardcoded.

## Status

- [x] Phase 0 — Scaffolding & Config
- [x] Phase 1 — CSV Upload (backend)
- [x] Phase 2 — Rows (backend)
- [x] Phase 3 — Ask / LLM (backend)
- [ ] Phase 4 — Frontend
- [ ] Phase 5 — Integration & Docs
