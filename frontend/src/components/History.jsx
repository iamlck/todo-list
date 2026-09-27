import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { formatMinutes } from '../lib/progress'

/** A log of deleted tasks. Records what went and when; nothing to restore from. */
export default function History() {
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.deletedTasks().then(setEntries).catch((err) => setError(err.message))
  }, [])

  return (
    <div className="pad stack">
      <section className="card stack">
        <h1>Deleted tasks</h1>
        <p className="muted">
          A record of what has been removed. This is a history log, not a recycle bin — to
          bring something back, use <strong>Undo</strong> straight after deleting it, or add
          it again in the <Link to="/editor">plan editor</Link>.
        </p>
      </section>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {entries === null ? (
        <p className="muted pad">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="muted pad">Nothing has been deleted yet.</p>
      ) : (
        <section className="card">
          <ul className="history">
            {entries.map((entry) => (
              <li key={entry.id} className={entry.restored_at ? 'restored' : undefined}>
                <div className="row wrap gap between">
                  <strong>{entry.title}</strong>
                  <span className="muted small">
                    {new Date(entry.deleted_at).toLocaleString()}
                  </span>
                </div>
                <p className="muted small">
                  {entry.day_position ? `Day ${entry.day_position}` : 'Day unknown'}
                  {entry.day_title ? ` — ${entry.day_title}` : ''}
                  {entry.parent_title ? ` · under ${entry.parent_title}` : ''}
                  {entry.subtask_count > 0 && ` · ${entry.subtask_count} subtasks`}
                  {entry.was_completed && ' · was completed'}
                  {entry.minutes_spent > 0 && ` · ${formatMinutes(entry.minutes_spent)} recorded`}
                  {entry.reason === 'day' && ' · removed with its day'}
                </p>
                {entry.restored_at && <p className="ok small">Restored</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
