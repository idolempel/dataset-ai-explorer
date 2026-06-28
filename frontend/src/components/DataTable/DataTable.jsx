import { useRows } from "../../hooks/useRows";
import EmptyState from "../common/EmptyState";
import ErrorBanner from "../common/ErrorBanner";
import Spinner from "../common/Spinner";
import Pagination from "./Pagination";
import TableFilters from "./TableFilters";
import "./DataTable.css";

/**
 * Browses rows of the active dataset via GET /rows.
 *
 * Owns a `useRows` instance keyed by `dataset.dataset_id`. The hook resets all
 * query state whenever the dataset changes, so the table always reflects the
 * currently active dataset.
 */
export default function DataTable({ dataset }) {
  const datasetId = dataset?.dataset_id ?? null;
  const rows = useRows(datasetId);

  const {
    data,
    isLoading,
    isError,
    error,
    page,
    pageSize,
    sortBy,
    sortDir,
    search,
    filters,
    changeSearch,
    changeFilter,
    clearFilters,
    changePageSize,
    toggleSort,
    goToPage,
  } = rows;

  if (!datasetId) return null;

  // Prefer columns from the latest response; fall back to the upload metadata so
  // filters/headers render before the first response arrives.
  const columns = data?.columns ?? dataset?.columns ?? [];
  const tableRows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 0;

  const showEmpty = !isLoading && !isError && data && tableRows.length === 0;

  return (
    <section className="datatable" aria-label="Dataset rows">
      <div className="datatable__head">
        <h2>{dataset?.original_filename?.replace('.csv', '') || 'Dataset Rows'}</h2>
        {isLoading && <Spinner label="Loading rows…" />}
      </div>

      <TableFilters
        columns={columns}
        search={search}
        filters={filters}
        onSearchChange={changeSearch}
        onFilterChange={changeFilter}
        onClear={clearFilters}
        disabled={isLoading && !data}
      />

      {isError && <ErrorBanner message={error} />}

      <div className="datatable__scroll">
        <table className="datatable__table">
          <thead>
            <tr>
              {columns.map((col) => {
                const isSorted = sortBy === col.name;
                const indicator = isSorted
                  ? sortDir === "asc"
                    ? " ▲"
                    : " ▼"
                  : "";
                return (
                  <th key={col.name}>
                    <button
                      type="button"
                      className="datatable__sort"
                      onClick={() => toggleSort(col.name)}
                      title={`Sort by ${col.name}`}
                    >
                      <span>{col.name}</span>
                      <span className={`badge badge--${col.type}`}>
                        {col.type}
                      </span>
                      <span className="datatable__sort-ind">{indicator}</span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => (
                  <td key={col.name}>{formatCell(row[col.name])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {showEmpty && (
          <EmptyState
            title="No matching rows"
            message="Try adjusting or clearing your search and filters."
          />
        )}
      </div>

      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        rowsOnPage={tableRows.length}
        onPageChange={goToPage}
        onPageSizeChange={changePageSize}
        disabled={isLoading}
      />
    </section>
  );
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return <span className="datatable__null">—</span>;
  }
  return String(value);
}
