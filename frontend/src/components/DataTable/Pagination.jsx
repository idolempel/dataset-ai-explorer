import { PAGE_SIZE_OPTIONS } from "../../hooks/useRows";

/**
 * Pagination controls: page-size selector, prev/next, and a status line showing
 * the current row range and totals.
 */
export default function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  rowsOnPage,
  onPageChange,
  onPageSizeChange,
  disabled,
}) {
  const safeTotalPages = totalPages || 0;
  const canPrev = page > 1 && !disabled;
  const canNext = page < safeTotalPages && !disabled;

  const firstRow = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastRow = total === 0 ? 0 : firstRow + rowsOnPage - 1;

  return (
    <div className="pagination">
      <div className="pagination__info">
        {total === 0 ? (
          <span>No rows</span>
        ) : (
          <span>
            Showing <strong>{firstRow}</strong>–<strong>{lastRow}</strong> of{" "}
            <strong>{total}</strong> rows · Page <strong>{page}</strong> of{" "}
            <strong>{safeTotalPages}</strong>
          </span>
        )}
      </div>

      <div className="pagination__controls">
        <label className="pagination__size">
          <span>Rows per page</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            disabled={disabled}
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>

        <div className="pagination__buttons">
          <button
            type="button"
            onClick={() => onPageChange(1)}
            disabled={!canPrev}
            aria-label="First page"
          >
            «
          </button>
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={!canPrev}
            aria-label="Previous page"
          >
            ‹ Prev
          </button>
          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={!canNext}
            aria-label="Next page"
          >
            Next ›
          </button>
          <button
            type="button"
            onClick={() => onPageChange(safeTotalPages)}
            disabled={!canNext}
            aria-label="Last page"
          >
            »
          </button>
        </div>
      </div>
    </div>
  );
}
