/**
 * Global search box plus per-column substring filters.
 *
 * `columns` is the array of { name, type } from the rows response. Per-column
 * filters map cleanly to the backend's `filter.<column>=<value>` contract.
 */
export default function TableFilters({
  columns,
  search,
  filters,
  onSearchChange,
  onFilterChange,
  onClear,
  disabled,
}) {
  const hasActiveFilters =
    Boolean(search) || Object.values(filters || {}).some((v) => v);

  return (
    <div className="filters">
      <div className="filters__row">
        <label className="filters__search">
          <span className="filters__label">Search all columns</span>
          <input
            type="search"
            value={search}
            placeholder="Type to search…"
            onChange={(e) => onSearchChange(e.target.value)}
            disabled={disabled}
          />
        </label>

        <button
          type="button"
          className="btn-link filters__clear"
          onClick={onClear}
          disabled={disabled || !hasActiveFilters}
        >
          Clear all
        </button>
      </div>

      {columns && columns.length > 0 && (
        <div className="filters__columns">
          {columns.map((col) => (
            <label key={col.name} className="filters__col">
              <span className="filters__col-name">{col.name}</span>
              <input
                type="text"
                value={filters?.[col.name] ?? ""}
                placeholder={`Filter ${col.name}`}
                onChange={(e) => onFilterChange(col.name, e.target.value)}
                disabled={disabled}
              />
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
