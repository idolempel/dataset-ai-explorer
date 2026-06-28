# Full-Stack Dataset Explorer with AI Insights

## 1. Project Overview

Full-Stack Dataset Explorer with AI Insights is a web application that lets you
upload a CSV dataset, browse it in an interactive table with search, filtering, and
sorting, and ask natural-language questions that are answered with AI-generated
insights based on your uploaded data.

Under the hood, each question is answered by translating it into a safe, read-only
SQL query against your dataset and then summarizing the results in plain English, so
the answers are grounded in the actual data you uploaded rather than generic model
knowledge.

## 2. Live Demo

- **Frontend:** https://dataset-ai-explorer-gilt.vercel.app
- **Backend API:** https://dataset-explorer-backend-kha9.onrender.com
- **API Docs:** https://dataset-explorer-backend-kha9.onrender.com/docs

> Note: The backend is hosted on Render's free tier, so the first request after a
> period of inactivity may take longer while the service wakes up.

## 3. Features

- CSV upload
- Dynamic dataset/table creation
- Dataset metadata and inferred column types
- Paginated rows browsing
- Global search across all columns
- Per-column filters
- Typed sorting for numeric columns
- Natural-language AI Q&A
- Result preview for AI answers
- Loading, error, and empty states

## 4. Tech Stack

**Backend**

- Python
- FastAPI
- SQLite
- Anthropic Claude API
- pytest
- Render (hosting)

**Frontend**

- React
- Vite
- CSS
- ESLint
- Vercel (hosting)

## 5. Architecture

High-level flow:

```
CSV upload
  → backend parses the CSV
  → backend creates a sanitized SQLite table
  → backend stores dataset metadata and inferred column types
  → frontend fetches rows with pagination / search / filter / sort
  → user asks a natural-language question
  → backend asks Claude to generate SQL
  → sql_guard validates the generated SQL
  → backend executes the read-only query
  → Claude summarizes the query results
  → frontend displays the answer and a result preview
```

Each uploaded CSV becomes its own SQLite data table, registered in a `datasets`
metadata table that also stores the inferred logical type for each column. The rows
endpoint reads from that table with parameterized queries, while the ask endpoint
uses the schema metadata as context for the language model.

```
.
├── backend/    # FastAPI app, SQLite access, services, sql_guard, tests
└── frontend/   # React (Vite) single-page app
```

## 6. Setup / Running Locally

Prerequisites: Python 3.11+ and Node.js 18+.

### Backend

```powershell
cd backend
copy .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

The backend runs on `http://localhost:8000` (interactive docs at
`http://localhost:8000/docs`). Edit `.env` and set your `ANTHROPIC_API_KEY` before
using the AI Q&A feature.

> If the virtual environment does not exist yet, create it first with
> `python -m venv .venv`.

Run the backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Frontend

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

The frontend runs on the Vite dev server (printed in the terminal, typically
`http://localhost:5173`). Ensure `VITE_API_BASE_URL` in `.env` points to your backend
(`http://localhost:8000` by default).

Frontend checks:

```markdown
```powershell
npm run lint
npm run build
```

## 7. Environment Variables

**Backend** (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key used to call the Anthropic Claude API. |
| `ANTHROPIC_MODEL` | Claude model identifier used for SQL generation and summarization. |
| `DATABASE_PATH` | Path to the SQLite database file. |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins. |
| `MAX_LLM_RESULT_ROWS` | Maximum number of rows returned to the UI/LLM from a query. |
| `MAX_UPLOAD_BYTES` | Maximum allowed CSV upload size in bytes. |

**Frontend** (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Base URL of the backend API. |

> Never commit real `.env` files or API keys. Use the provided `.env.example`
> templates and configure secrets through your hosting provider's environment
> settings in production.

## 8. Deployment

- The **backend** is deployed on **Render**.
- The **frontend** is deployed on **Vercel**.
- Vercel sets `VITE_API_BASE_URL` to the deployed Render backend URL.
- Render sets `CORS_ORIGINS` to include the deployed Vercel frontend URL.
- Backend secrets such as `ANTHROPIC_API_KEY` are configured as Render environment
  variables and are not committed to GitHub.
- Because this implementation uses SQLite, file persistence may be limited on
  free-tier deployment platforms (uploaded datasets can be cleared when the service
  restarts). For a production version, persistent storage or a managed database would
  be preferred.

## 9. API Overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload a CSV and create a dataset. |
| GET | `/rows` | Fetch paginated rows with search, filters, and sorting. |
| GET | `/datasets` | List uploaded datasets. |
| GET | `/datasets/{id}/schema` | Fetch a dataset's schema/columns. |
| POST | `/ask` | Ask a natural-language question about a dataset. |

Full, interactive documentation (Swagger UI) is available at `/docs` — locally at
`http://localhost:8000/docs` and at the deployed API docs URL listed above.

## 10. Security and Safety Decisions

- API keys are loaded from environment variables and are never committed to the
  repository.
- Uploaded table and column names are sanitized and quoted before being used as SQL
  identifiers, preventing user-controlled CSV filenames or headers from being
  interpreted as SQL code.
- User-provided search terms, filters, and inserted row values are passed as bound
  SQL parameters, so they are treated as data rather than executable SQL.
- LLM-generated SQL is validated before execution.
- Only `SELECT`/CTE-style read queries are allowed.
- Destructive SQL keywords such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
  `ATTACH`, and `PRAGMA` are rejected.
- Result limits are enforced before query results are returned to the UI or sent back
  to the LLM.
- The backend returns the generated SQL for transparency/debugging, but the final
  user-facing UI does not display it.

## 11. Design Decisions / Assumptions

- SQLite data table values are stored as `TEXT` for ingestion robustness. This avoids
  rejecting messy CSV rows during upload.
- Logical column types are inferred and stored as dataset metadata. These types are
  used for display, LLM schema context, and typed sorting.
- Numeric sorting uses `CAST` based on trusted internal metadata, so integer and float
  columns sort numerically even though values are stored as `TEXT`.
- Date columns are currently sorted as text. ISO-formatted dates such as
  `YYYY-MM-DD` sort correctly lexicographically, but other date formats would require
  normalization during ingestion.
- The frontend uses lightweight custom React table components instead of a heavy table
  library, keeping the implementation easier to inspect for a take-home assignment.

## 12. Testing

- The backend test suite passes (`pytest`).
- Frontend lint and build pass (`npm run lint`, `npm run build`).
- Manual integration was tested locally and in production with the flow:
  upload CSV → browse rows → search/filter/sort → ask an AI question →
  view the answer and result preview.
- Frontend behavior was also checked when the backend is unavailable, confirming that
  errors are surfaced gracefully.

## 13. What I'd Do Next

- Improve typed data handling by normalizing dates and storing typed values alongside
  the original CSV text, so filtering, sorting, and AI-generated SQL can handle dates
  and numbers more reliably.
- Support larger and messier datasets with streaming ingestion, background jobs,
  progress indicators, and clearer validation errors for malformed CSV files.
- Make AI analysis more robust for complex questions such as rolling averages, sliding
  windows, anomaly detection, and time-period comparisons, without sending too many
  raw rows to the LLM. Add charts and visual summaries for AI result previews and
  common aggregations.
- Add multi-table analysis so users can upload related datasets, define relationships
  between tables, and ask AI questions that require joins across datasets.
- Add authentication and persistent storage so each user can securely keep, revisit,
  and manage their own datasets across sessions and deployments.
