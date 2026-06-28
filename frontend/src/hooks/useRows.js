import { useCallback, useEffect, useRef, useState } from "react";

import { fetchRows } from "../api/client";

export const RowsStatus = {
  Idle: "idle",
  Loading: "loading",
  Success: "success",
  Error: "error",
};

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 25;
const DEBOUNCE_MS = 350;

/**
 * Manages all GET /rows state for a single dataset: pagination, sorting, global
 * search, and per-column filters.
 *
 * Behavior:
 * - Fetches page 1 automatically when `datasetId` becomes available.
 * - Any change to search, filters, page size, or sort resets the page to 1.
 * - Text inputs (search/filters) are debounced before triggering a request.
 * - An incrementing request id guards against out-of-order responses.
 *
 * @param {number|null|undefined} datasetId
 */
export function useRows(datasetId) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [sortBy, setSortBy] = useState(null);
  const [sortDir, setSortDir] = useState("asc");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({});

  const [data, setData] = useState(null);
  const [status, setStatus] = useState(RowsStatus.Idle);
  const [error, setError] = useState(null);

  const requestIdRef = useRef(0);

  // Reset everything when the active dataset changes.
  useEffect(() => {
    setPage(1);
    setPageSize(DEFAULT_PAGE_SIZE);
    setSortBy(null);
    setSortDir("asc");
    setSearch("");
    setFilters({});
    setData(null);
    setStatus(RowsStatus.Idle);
    setError(null);
  }, [datasetId]);

  // Debounced snapshot of the text inputs so typing doesn't spam the API.
  const [debounced, setDebounced] = useState({ search: "", filters: {} });
  useEffect(() => {
    const handle = setTimeout(() => {
      setDebounced({ search, filters });
    }, DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [search, filters]);

  // The actual fetch effect.
  useEffect(() => {
    if (!datasetId) return;

    const requestId = ++requestIdRef.current;
    setStatus(RowsStatus.Loading);
    setError(null);

    fetchRows({
      datasetId,
      page,
      pageSize,
      sortBy,
      sortDir,
      search: debounced.search,
      filters: debounced.filters,
    })
      .then((result) => {
        if (requestId !== requestIdRef.current) return; // stale response
        setData(result);
        setStatus(RowsStatus.Success);
      })
      .catch((err) => {
        if (requestId !== requestIdRef.current) return;
        setError(err?.message || "Failed to load rows.");
        setStatus(RowsStatus.Error);
      });
  }, [datasetId, page, pageSize, sortBy, sortDir, debounced]);

  // --- Setters that enforce "reset to page 1" semantics ---------------------

  const changeSearch = useCallback((value) => {
    setSearch(value);
    setPage(1);
  }, []);

  const changeFilter = useCallback((column, value) => {
    setFilters((prev) => ({ ...prev, [column]: value }));
    setPage(1);
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({});
    setSearch("");
    setPage(1);
  }, []);

  const changePageSize = useCallback((size) => {
    setPageSize(size);
    setPage(1);
  }, []);

  /**
   * Toggle sorting for a column: unsorted -> asc -> desc -> unsorted.
   * Changing the sort column/direction resets to page 1.
   */
  const toggleSort = useCallback(
    (column) => {
      setPage(1);
      if (sortBy !== column) {
        setSortBy(column);
        setSortDir("asc");
      } else if (sortDir === "asc") {
        setSortDir("desc");
      } else {
        // Was descending -> clear sort.
        setSortBy(null);
        setSortDir("asc");
      }
    },
    [sortBy, sortDir]
  );

  const goToPage = useCallback((nextPage) => {
    setPage((current) => (nextPage >= 1 ? nextPage : current));
  }, []);

  return {
    // query state
    page,
    pageSize,
    sortBy,
    sortDir,
    search,
    filters,
    // response state
    data,
    status,
    error,
    isLoading: status === RowsStatus.Loading,
    isError: status === RowsStatus.Error,
    isSuccess: status === RowsStatus.Success,
    // actions
    changeSearch,
    changeFilter,
    clearFilters,
    changePageSize,
    toggleSort,
    goToPage,
  };
}
