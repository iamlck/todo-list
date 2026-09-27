import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { formatMinutes } from '../lib/progress'

/**
 * Administration: every account, what it holds, and the ability to grant
 * admin rights or remove an account.
 *
 * Counts and totals only — an administrator can see how much work an account
 * holds, not read the notes inside it.
 */
export default function Admin() {
  const { user } = useAuth()
  const [users, setUsers] = useState(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [deleting, setDeleting] = useState(null) // the user being removed
  const [password, setPassword] = useState('')
  const [confirmEmail, setConfirmEmail] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async (q = '') => {
    try {
      setUsers(await api.adminUsers(q))
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function toggleAdmin(target) {
    setError(null)
    try {
      await api.adminSetAdmin(target.id, !target.is_admin)
      await load(query)
      setNotice(
        `${target.email} is ${target.is_admin ? 'no longer an administrator' : 'now an administrator'}.`,
      )
    } catch (err) {
      setError(err.message)
    }
  }

  async function confirmDelete(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.adminDeleteUser(deleting.id, password, confirmEmail)
      setNotice(`${deleting.email} was deleted.`)
      setDeleting(null)
      setPassword('')
      setConfirmEmail('')
      await load(query)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="pad stack">
      <section className="card stack">
        <h1>Users</h1>
        <p className="muted">
          {users ? `${users.length} account${users.length === 1 ? '' : 's'}.` : 'Loading…'} You
          can see how much work each account holds, not what is in it.
        </p>

        <form
          className="row gap"
          onSubmit={(e) => {
            e.preventDefault()
            load(query)
          }}
        >
          <label className="visually-hidden" htmlFor="admin-search">
            Search by email
          </label>
          <input
            id="admin-search"
            placeholder="Search by email…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="secondary">Search</button>
          {query && (
            <button
              type="button"
              className="link"
              onClick={() => {
                setQuery('')
                load('')
              }}
            >
              Clear
            </button>
          )}
        </form>

        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="ok" role="status">{notice}</p>}
      </section>

      {users && users.length > 0 && (
        <section className="card">
          <ul className="admin-users">
            {users.map((row) => (
              <li key={row.id}>
                <div className="row wrap gap between">
                  <strong>
                    {row.email}
                    {row.is_admin && <span className="badge admin-badge">admin</span>}
                    {row.id === user?.id && <span className="muted small"> · you</span>}
                  </strong>
                  <span className="muted small">
                    joined {new Date(row.created_at).toLocaleDateString()}
                  </span>
                </div>

                <p className="muted small">
                  {row.onboarded
                    ? `${row.days} days · ${row.tasks} tasks · ${row.completed_tasks} completed · ${formatMinutes(row.minutes_spent)}`
                    : 'No plan set up yet'}
                  {row.start_date && ` · starts ${row.start_date}`}
                  {row.last_activity &&
                    ` · last active ${new Date(row.last_activity).toLocaleDateString()}`}
                </p>

                <div className="row gap wrap">
                  <button type="button" className="link" onClick={() => toggleAdmin(row)}>
                    {row.is_admin ? 'Remove admin' : 'Make admin'}
                  </button>
                  {row.id !== user?.id && (
                    <button
                      type="button"
                      className="link danger"
                      onClick={() => {
                        setDeleting(row)
                        setPassword('')
                        setConfirmEmail('')
                        setNotice(null)
                      }}
                    >
                      Delete account
                    </button>
                  )}
                </div>

                {deleting?.id === row.id && (
                  <form className="stack narrow delete-form" onSubmit={confirmDelete}>
                    <p className="warn-text">
                      <strong>This cannot be undone.</strong> It removes their plan, progress,
                      notes and recorded time.
                    </p>

                    <label htmlFor={`pw-${row.id}`}>Your password</label>
                    <input
                      id={`pw-${row.id}`}
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />

                    <label htmlFor={`em-${row.id}`}>
                      Type <strong>{row.email}</strong> to confirm
                    </label>
                    <input
                      id={`em-${row.id}`}
                      type="email"
                      required
                      value={confirmEmail}
                      onChange={(e) => setConfirmEmail(e.target.value)}
                    />

                    <div className="row gap">
                      <button type="submit" className="danger-button" disabled={busy}>
                        {busy ? 'Deleting…' : 'Permanently delete'}
                      </button>
                      <button type="button" className="secondary" onClick={() => setDeleting(null)}>
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {users && users.length === 0 && <p className="muted pad">No accounts match that search.</p>}
    </div>
  )
}
