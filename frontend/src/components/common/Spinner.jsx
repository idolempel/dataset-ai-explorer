export default function Spinner({ label = "Loading…" }) {
  return (
    <span className="spinner" role="status" aria-live="polite">
      <span className="spinner__dot" aria-hidden="true" />
      <span className="spinner__label">{label}</span>
    </span>
  );
}
