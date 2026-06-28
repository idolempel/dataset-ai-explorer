import { useCallback, useEffect, useRef, useState } from "react";

import { askDataset } from "../api/client";

export const AskStatus = {
  Idle: "idle",
  Loading: "loading",
  Success: "success",
  Error: "error",
};

/**
 * Manages the POST /ask request lifecycle for a single dataset.
 *
 * Notably, the previous `result` is kept visible while a new request is in flight
 * and even if the new request errors — it is only replaced on a successful
 * response, or cleared explicitly via `reset()`. A request-id guard discards
 * out-of-order responses.
 *
 * @param {number|null|undefined} datasetId
 */
export function useAsk(datasetId) {
  const [status, setStatus] = useState(AskStatus.Idle);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const requestIdRef = useRef(0);

  // Clear everything when the active dataset changes.
  useEffect(() => {
    requestIdRef.current += 1; // invalidate any in-flight request
    setStatus(AskStatus.Idle);
    setResult(null);
    setError(null);
  }, [datasetId]);

  const ask = useCallback(
    async (question) => {
      const trimmed = (question || "").trim();
      if (!datasetId || !trimmed) return null;

      const requestId = ++requestIdRef.current;
      setStatus(AskStatus.Loading);
      setError(null);
      // Intentionally keep the previous `result` visible during loading.

      try {
        const data = await askDataset({ datasetId, question: trimmed });
        if (requestId !== requestIdRef.current) return null; // stale
        setResult(data);
        setStatus(AskStatus.Success);
        return data;
      } catch (err) {
        if (requestId !== requestIdRef.current) return null; // stale
        setError(err?.message || "Failed to get an answer.");
        setStatus(AskStatus.Error);
        return null;
      }
    },
    [datasetId]
  );

  const reset = useCallback(() => {
    requestIdRef.current += 1;
    setStatus(AskStatus.Idle);
    setResult(null);
    setError(null);
  }, []);

  return {
    status,
    result,
    error,
    ask,
    reset,
    isLoading: status === AskStatus.Loading,
    isSuccess: status === AskStatus.Success,
    isError: status === AskStatus.Error,
  };
}
