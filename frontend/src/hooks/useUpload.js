import { useCallback, useState } from "react";

import { uploadCsv } from "../api/client";

// Upload lifecycle statuses.
export const UploadStatus = {
  Idle: "idle",
  Loading: "loading",
  Success: "success",
  Error: "error",
};

/**
 * Encapsulates the POST /upload request state.
 * Returns the current status, the parsed result, any error message, and an
 * `upload(file)` function plus a `reset()` helper.
 */
export function useUpload() {
  const [status, setStatus] = useState(UploadStatus.Idle);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const upload = useCallback(async (file) => {
    setStatus(UploadStatus.Loading);
    setError(null);
    setResult(null);
    try {
      const data = await uploadCsv(file);
      setResult(data);
      setStatus(UploadStatus.Success);
      return data;
    } catch (err) {
      setError(err?.message || "Upload failed.");
      setStatus(UploadStatus.Error);
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setStatus(UploadStatus.Idle);
    setResult(null);
    setError(null);
  }, []);

  return {
    status,
    result,
    error,
    upload,
    reset,
    isLoading: status === UploadStatus.Loading,
    isSuccess: status === UploadStatus.Success,
    isError: status === UploadStatus.Error,
  };
}
