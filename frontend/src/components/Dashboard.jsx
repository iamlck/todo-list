import { Link, useNavigate } from 'react-router-dom'
import { usePlan } from '../context/PlanContext'
import ProgressBar from './ProgressBar'
import {
  STATUS_LABELS,
  currentDay,
  dayMinutes,
  dayProgress,
  dayStatus,
  formatMinutes,
  overallProgress,
  statusCounts,
  totalMinutes,
} from '../lib/progress'

export default function Dashboard() {
  const { days, startDate, setStartDate } = usePlan()
  const navigate = useNavigate()

  const overall = overallProgress(days)
  const counts = statusCounts(days)
  const today = currentDay(startDate, days.length)

  if (days.length === 0) {
    return (
      <div className="pad">
        <h1>Your plan is empty</h1>
        <p className="muted">
          Add your first day in the <Link to="/editor">plan editor</Link> to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="pad stack">
      <section className="card stack">
        <h1>{days.length}-Day Learning Tracker</h1>

        <div className="row wrap gap">
          <div>
            <label htmlFor="start-date">Start date</label>
            <input
              id="start-date"
              type="date"
              value={startDate ?? ''}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="today-box">
            <span className="muted">Current day</span>
            <strong>{today ? `Day ${today}` : 'Set a start date'}</strong>
          </div>
          <button
            type="button"
            className="primary"
            disabled={!today}
            onClick={() => navigate(`/day/${today}`)}
          >
            Continue today
          </button>
        </div>
      </section>

      <section className="card stack">
        <h2>Progress</h2>
        <ProgressBar label="Overall" {...overall} />
        <ul className="status-breakdown">
          <li className="not-started">
            <strong>{counts['not-started']}</strong> <span>Not started</span>
          </li>
          <li className="in-progress">
            <strong>{counts['in-progress']}</strong> <span>In progress</span>
          </li>
          <li className="completed">
            <strong>{counts.completed}</strong> <span>Completed</span>
          </li>
        </ul>
        <p className="muted">Total time recorded: {formatMinutes(totalMinutes(days))}</p>
      </section>

      <section className="card stack">
        <h2>All days</h2>
        <ul className="day-grid">
          {days.map((day) => {
            const status = dayStatus(day)
            const { completed, total } = dayProgress(day)
            const isToday = day.position === today
            return (
              <li key={day.id}>
                <Link
                  to={`/day/${day.position}`}
                  className={`day-card ${status}${isToday ? ' is-today' : ''}`}
                  aria-current={isToday ? 'date' : undefined}
                >
                  <span className="day-number">Day {day.position}</span>
                  <span className="day-title">{day.title || 'Untitled'}</span>
                  <span className="day-status">{STATUS_LABELS[status]}</span>
                  <span className="muted">
                    {completed}/{total} tasks · {formatMinutes(dayMinutes(day))}
                  </span>
                  {isToday && <span className="badge">Today</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </section>
    </div>
  )
}
