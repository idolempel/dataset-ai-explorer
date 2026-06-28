import { useCallback, useRef, useState } from "react";

import { useUpload } from "../../hooks/useUpload";
import ErrorBanner from "../common/ErrorBanner";
import Spinner from "../common/Spinner";
import "./FileUpload.css";

/**
 * CSV upload UI with drag-and-drop + file picker.
 * On a successful upload it shows a summary and lifts the dataset up via
 * `onUploaded(datasetResult)`.
 */
export default function FileUpload({ onUploaded }) {
  const { result, error, upload, reset, isLoading, isSuccess, isError } =
    useUpload();
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedName, setSelectedName] = useState("");

  const handleFile = useCallback(
    async (file) => {
      if (!file) return;
      setSelectedName(file.name);
      const data = await upload(file);
      if (data && typeof onUploaded === "function") {
        onUploaded(data);
      }
    },
    [upload, onUploaded]
  );

  const onInputChange = (event) => {
    const file = event.target.files && event.target.files[0];
    handleFile(file);
  };

  const onDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    handleFile(file);
  };

  const onDragOver = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  const openPicker = () => {
    if (!isLoading && inputRef.current) {
      inputRef.current.click();
    }
  };

  const onReset = () => {
    setSelectedName("");
    if (inputRef.current) inputRef.current.value = "";
    reset();
  };

  return (
    <section className="upload" aria-label="CSV upload">
      <div
        className={
          "upload__dropzone" +
          (isDragging ? " upload__dropzone--active" : "") +
          (isLoading ? " upload__dropzone--disabled" : "")
        }
        onClick={openPicker}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") openPicker();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={onInputChange}
          className="upload__input"
          disabled={isLoading}
        />
        <p className="upload__hint">
          <strong>Click to choose a CSV</strong> or drag &amp; drop it here
        </p>
        {selectedName && !isError && (
          <p className="upload__filename">{selectedName}</p>
        )}
        {isLoading && <Spinner label="Uploading & parsing…" />}
      </div>

      {isError && (
        <ErrorBanner message={error} onDismiss={onReset} />
      )}

      {isSuccess && result && (
        <UploadSummary result={result} onReset={onReset} />
      )}
    </section>
  );
}

function UploadSummary({ result, onReset }) {
  return (
    <div className="upload__summary surface-card" aria-live="polite">
      <details className="upload__details">
        <summary className="upload__summary-toggle">
          <span className="upload__summary-check" aria-hidden="true">
            ✓
          </span>
          Upload successful! Click to view dataset details
        </summary>

        <div className="upload__details-body">
          <dl className="upload__meta">
            <div>
              <dt>File</dt>
              <dd>{result.original_filename}</dd>
            </div>
            <div>
              <dt>Rows</dt>
              <dd>{result.row_count}</dd>
            </div>
            <div>
              <dt>Columns</dt>
              <dd>{result.columns?.length ?? 0}</dd>
            </div>
          </dl>

          <h4 className="upload__cols-title">Detected columns &amp; types</h4>
          <ul className="upload__cols">
            {(result.columns || []).map((col) => (
              <li key={col.name} className="upload__col">
                <span className="upload__col-name">{col.name}</span>
                <span className={`badge badge--${col.type}`}>{col.type}</span>
              </li>
            ))}
          </ul>

          <button type="button" className="btn-link" onClick={onReset}>
            Upload another
          </button>
        </div>
      </details>
    </div>
  );
}
