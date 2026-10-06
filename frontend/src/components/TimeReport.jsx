import { useState } from 'react'
import { Link } from 'react-router-dom'
import { usePlan } from '../context/PlanContext'
import ExportData from './ExportData'
import { exportRows } from '../lib/export'
import {
  STATUS_LABELS,
  formatMinutes,
  longestTasks,
  timeByMainTask,
  timePerDay,
  timeSummary,
} from '../lib/progress'

/**
 * Where the time went.
 *
 * Every figure here is derived from the plan already in memory, so it needs
 * no extra request and can never disagree with the day views.
 *
 * All three charts show one measure — minutes — so they use a single hue
 * rather than a categorical palette: colour carries no meaning here, length
 * does. A table view sits behind each chart for the same reason.
 */
export default function TimeReport() {
  const { days, startDate } = usePlan()
  const [showTable, setShowTable] = useState(false)

  const summary = timeSummary(days)
  const perDay = timePerDay(days)
  const bySubject = timeByMainTask(days).filter((r) => r.minutes > 0)
  const top = longestTasks(days, 10)
  const rows = exportRows(days, startDate)

  if (summary.total === 0) {
    return (
      <div className="pad stack">
        <section className="card stack">
          <h1>Time</h1>
          <ExportData />
          <p className="muted">
            No time recorded yet. Open a day and press <strong>▶ Start</strong> on a task, or
            click its time to type minutes in directly. <Link to="/">Back to the dashboard</Link>.
          </p>
        </section>
      </div>
    )
  }

  const dayMax = Math.max(...perDay.map((d) => d.minutes), 1)
  const subjectMax = Math.max(...bySubject.map((r) => r.minutes), 1)

  return (
    <div className="pad stack">
      <section className="card stack">
        <div className="row wrap gap between">
          <h1>Time</h1>
          <ExportData />
        </div>
        <ul className="stat-tiles">
          <li>
            <strong>{formatMinutes(summary.total)}</strong>
            <span>Total recorded</span>
          </li>
          <li>
            <strong>{summary.trackedDays}</strong>
            <span>Days worked</span>
          </li>
          <li>
            <strong>{formatMinutes(summary.averagePerTrackedDay)}</strong>
            <span>Average per day worked</span>
          </li>
          <li>
            <strong>{summary.busiest ? `Day ${summary.busiest.position}` : '—'}</strong>
            <span>
              Busiest day
              {summary.busiest && ` · ${formatMinutes(summary.busiest.minutes)}`}
            </span>
          </li>
        </ul>
        <p className="muted small">
          The average covers days you actually worked, not every day in the plan.
        </p>
      </section>

      <section className="card stack">
        <div className="row wrap gap between">
          <h2>Time per day</h2>
          <button type="button" className="link" onClick={() => setShowTable((v) => !v)}>
            {showTable ? 'Show chart' : 'Show as table'}
          </button>
        </div>

        {showTable ? (
          <table className="data-table">
            <caption className="visually-hidden">Minutes recorded on each day</caption>
            <thead>
              <tr>
                <th scope="col">Day</th>
                <th scope="col">Title</th>
                <th scope="col" className="numeric">Time</th>
              </tr>
            </thead>
            <tbody>
              {perDay.map((d) => (
                <tr key={d.id}>
                  <th scope="row">{d.position}</th>
                  <td>{d.title || '—'}</td>
                  <td className="numeric">{formatMinutes(d.minutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <ol className="col-chart" aria-label="Time recorded per day">
            {perDay.map((d) => (
              <li key={d.id} title={`Day ${d.position}${d.title ? ` — ${d.title}` : ''}: ${formatMinutes(d.minutes)}`}>
                <Link to={`/day/${d.position}`} className="col-link">
                  <span className="col-track">
                    <span
                      className="col-fill"
                      style={{ height: `${Math.round((d.minutes / dayMax) * 100)}%` }}
                    />
                  </span>
                  <span className="col-label">{d.position}</span>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="card stack">
        <h2>By subject</h2>
        <p className="muted small">
          Main tasks of the same name added up across every day.
        </p>
        <ul className="bar-chart" aria-label="Time recorded per subject">
          {bySubject.map((row) => (
            <li key={row.title}>
              <span className="bar-label">{row.title}</span>
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{ width: `${Math.round((row.minutes / subjectMax) * 100)}%` }}
                />
              </span>
              <span className="bar-value">{formatMinutes(row.minutes)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card stack">
        <h2>Longest tasks</h2>
        {top.length === 0 ? (
          <p className="muted">No individual task has time against it yet.</p>
        ) : (
          <table className="data-table">
            <caption className="visually-hidden">Individual tasks with the most time recorded</caption>
            <thead>
              <tr>
                <th scope="col">Task</th>
                <th scope="col">Day</th>
                <th scope="col" className="numeric">Time</th>
              </tr>
            </thead>
            <tbody>
              {top.map((row) => (
                <tr key={row.id}>
                  <td>
                    {row.title}
                    {row.parent && <span className="muted small"> · {row.parent}</span>}
                    {row.completed && <span className="badge done-badge">done</span>}
                  </td>
                  <td>
                    <Link to={`/day/${row.dayPosition}`}>Day {row.dayPosition}</Link>
                  </td>
                  <td className="numeric">{formatMinutes(row.minutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card stack">
        <h2>All tasks</h2>
        <p className="muted small">
          Every task and subtask with its status, time and carry-forward history — the same
          rows the CSV export contains.
        </p>
        <div className="table-scroll">
          <table className="data-table">
            <caption className="visually-hidden">Every task in the plan</caption>
            <thead>
              <tr>
                <th scope="col">Day</th>
                <th scope="col">Task</th>
                <th scope="col">Status</th>
                <th scope="col" className="numeric">Time</th>
                <th scope="col" className="numeric">Carried</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <th scope="row">
                    <Link to={`/day/${r.day}`}>{r.day}</Link>
                  </th>
                  <td>
                    {r.main_task}
                    {r.subtask && <span className="muted small"> › {r.subtask}</span>}
                  </td>
                  <td>{STATUS_LABELS[r.status]}</td>
                  <td className="numeric">{formatMinutes(r.minutes_spent)}</td>
                  <td className="numeric">{r.carried_count || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
