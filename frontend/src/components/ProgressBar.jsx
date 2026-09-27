export default function ProgressBar({ label, completed, total, percent }) {
  return (
    <div className="progress">
      <div className="progress-head">
        <span>{label}</span>
        <span className="muted">
          {completed}/{total} · {percent}%
        </span>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-label={label}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
