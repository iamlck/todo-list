import { Link, useNavigate } from 'react-router-dom'

export default function DayNavigation({ position, dayCount }) {
  const navigate = useNavigate()
  const previous = position > 1 ? position - 1 : null
  const next = position < dayCount ? position + 1 : null

  return (
    <nav className="day-nav" aria-label="Day navigation">
      {previous ? (
        <Link to={`/day/${previous}`}>← Day {previous}</Link>
      ) : (
        <span className="muted disabled">← Previous</span>
      )}

      <select
        aria-label="Jump to day"
        value={position}
        // Client-side navigation: jumping days must not reload the plan.
        onChange={(e) => navigate(`/day/${e.target.value}`)}
      >
        {Array.from({ length: dayCount }, (_, i) => i + 1).map((n) => (
          <option key={n} value={n}>
            Day {n}
          </option>
        ))}
      </select>

      {next ? (
        <Link to={`/day/${next}`}>Day {next} →</Link>
      ) : (
        <span className="muted disabled">Next →</span>
      )}
    </nav>
  )
}
