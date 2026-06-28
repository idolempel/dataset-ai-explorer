// Centralized API client. The backend base URL comes exclusively from the
// VITE_API_BASE_URL environment variable (never hardcoded).

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

if (!BASE_URL) {
  // Surface a clear message during development if the env var is missing.
  console.warn(
    "VITE_API_BASE_URL is not set. Create frontend/.env from .env.example."
  );
}

/**
 * Error type that carries the HTTP status and the parsed backend detail.
 */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(response) {
  // The backend returns a consistent envelope: { "detail": "..." }.
  let detail = `Request failed with status ${response.status}`;
  try {
    const data = await response.json();
    if (data && typeof data.detail === "string") {
      detail = data.detail;
    } else if (data && Array.isArray(data.detail)) {
      // FastAPI validation errors (422) come back as a list.
      detail = data.detail
        .map((d) => d.msg || JSON.stringify(d))
        .join("; ");
    }
  } catch {
    // Non-JSON error body; keep the default message.
  }
  return new ApiError(detail, response.status);
}

/**
 * Upload a CSV file to POST /upload using multipart/form-data.
 * @param {File} file
 * @returns {Promise<object>} UploadResponse JSON
 */
export async function uploadCsv(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

/**
 * Fetch paginated/filtered rows from GET /rows.
 *
 * Per-column filters are sent as `filter.<column>=<value>` query params, matching
 * the backend contract. Empty values are omitted so they don't constrain results.
 *
 * @param {object} opts
 * @param {number} opts.datasetId
 * @param {number} [opts.page=1]
 * @param {number} [opts.pageSize=25]
 * @param {string|null} [opts.sortBy]
 * @param {"asc"|"desc"} [opts.sortDir="asc"]
 * @param {string} [opts.search]
 * @param {Record<string,string>} [opts.filters]
 * @returns {Promise<object>} RowsResponse JSON
 */
export async function fetchRows({
  datasetId,
  page = 1,
  pageSize = 25,
  sortBy = null,
  sortDir = "asc",
  search = "",
  filters = {},
} = {}) {
  const params = new URLSearchParams();
  params.set("dataset_id", String(datasetId));
  params.set("page", String(page));
  params.set("page_size", String(pageSize));

  if (sortBy) {
    params.set("sort_by", sortBy);
    params.set("sort_dir", sortDir === "desc" ? "desc" : "asc");
  }

  const trimmedSearch = (search || "").trim();
  if (trimmedSearch) {
    params.set("search", trimmedSearch);
  }

  for (const [col, value] of Object.entries(filters || {})) {
    const v = (value ?? "").toString().trim();
    if (v) {
      params.set(`filter.${col}`, v);
    }
  }

  const response = await fetch(`${BASE_URL}/rows?${params.toString()}`, {
    method: "GET",
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

/**
 * Ask a natural-language question about a dataset via POST /ask.
 * Sends a JSON body { dataset_id, question }; the backend runs NL → SQL → answer.
 *
 * @param {object} opts
 * @param {number} opts.datasetId
 * @param {string} opts.question
 * @returns {Promise<object>} AskResponse JSON
 *   { question, answer, generated_sql, result_preview[], row_count }
 */
export async function askDataset({ datasetId, question }) {
  const response = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, question }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export const apiBaseUrl = BASE_URL;
