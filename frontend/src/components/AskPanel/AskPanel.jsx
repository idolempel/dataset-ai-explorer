import { useState } from "react";

import { useAsk } from "../../hooks/useAsk";
import ErrorBanner from "../common/ErrorBanner";
import Spinner from "../common/Spinner";
import "./AskPanel.css";

/**
 * "Ask a question" panel for the active dataset.
 *
 * Submits POST /ask with { dataset_id, question }. Keeps the previous answer
 * visible while a new request is in flight (and even if it errors), per the
 * useAsk hook. The submit button is disabled while loading or when the question
 * is empty.
 */
export default function AskPanel({ dataset }) {
  const datasetId = dataset?.dataset_id ?? null;
  const { result, error, ask, reset, isLoading, isError } = useAsk(datasetId);
  const [question, setQuestion] = useState("");

  if (!datasetId) return null;

  const canSubmit = !isLoading && question.trim().length > 0;

  const onSubmit = (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    ask(question);
  };

  const onClear = () => {
    setQuestion("");
    reset();
  };

  return (
    <section className="ask" aria-label="Ask a question about the dataset">
      <div className="ask__head">
        <h2>Ask a question</h2>
        {isLoading && <Spinner label="Thinking…" />}
      </div>

      <form className="ask__form" onSubmit={onSubmit}>
        <label className="ask__label" htmlFor="ask-input">
          Ask in plain English about{" "}
          <strong>{dataset.original_filename}</strong>
        </label>
        <textarea
          id="ask-input"
          className="ask__input"
          value={question}
          placeholder="e.g. What is the average salary by department?"
          rows={2}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            // Submit on Ctrl/Cmd+Enter for convenience.
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
              onSubmit(e);
            }
          }}
          disabled={isLoading}
        />
        <div className="ask__actions">
          <button type="submit" className="btn-primary" disabled={!canSubmit}>
            {isLoading ? "Asking…" : "Ask"}
          </button>
          <button
            type="button"
            className="btn-link"
            onClick={onClear}
            disabled={isLoading || (!result && !question && !isError)}
          >
            Clear
          </button>
        </div>
      </form>

      {isError && <ErrorBanner message={error} />}

      {result && <AnswerCard result={result} stale={isLoading} />}
    </section>
  );
}

function AnswerCard({ result, stale }) {
  const { question, answer, result_preview } = result;

  return (
    <div className={"ask__answer" + (stale ? " ask__answer--stale" : "")}>
      {question && (
        <p className="ask__question" aria-label="Question asked">
          <span className="ask__q-label">Q:</span> {question}
        </p>
      )}

      <div className="ask__answer-text" aria-live="polite">
        {answer || <em>No answer text was returned.</em>}
      </div>

      <ResultPreview rows={result_preview} />
    </div>
  );
}

function ResultPreview({ rows }) {
  if (!rows || rows.length === 0) {
    return null;
  }

  // Derive a stable column order from the union of keys across preview rows.
  const columns = [];
  const seen = new Set();
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!seen.has(key)) {
        seen.add(key);
        columns.push(key);
      }
    }
  }

  return (
    <details className="ask__preview" open>
      <summary>Result preview ({rows.length} row{rows.length === 1 ? "" : "s"})</summary>
      <div className="ask__preview-scroll">
        <table className="ask__preview-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => (
                  <td key={col}>{formatCell(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return <span className="ask__null">—</span>;
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
