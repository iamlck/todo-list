import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { formatMinutes } from '../lib/progress'

/**
 * Permanently deletes the account. Unlike the other destructive actions in
 * this app, there is no undo for this one — so it states exactly what will be
 * lost and asks for both the password and the account's own email.
 */
export default function DeleteAccount() {
  const { user, signOut } = useAuth()
  const [summary, setSummary] = useState(null)
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [confirmEmail, setConfirmEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .accountSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.deleteAccount(password, confirmEmail)
      // Nothing left to show, so drop straight back to the sign-in screen.
      signOut()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <section className="card stack danger-zone">
      <h2>Delete account</h2>

      {summary ? (
        <p className="muted">
          This removes your account and everything on it: {summary.days} days,{' '}
          {summary.tasks} tasks, {summary.completed_tasks} completed, {summary.notes} with
          notes, and {formatMinutes(summary.minutes_spent)} of recorded time.
        </p>
      ) : (
        <p className="muted">This removes your account and everything on it.</p>
      )}
      <p className="warn-text">
        <strong>This cannot be undone.</strong> Back up first with{' '}
        <code>pg_dump</code> if you may want the data later.
      </p>

      {!open ? (
        <button type="button" className="danger-button" onClick={() => setOpen(true)}>
          Delete my account…
        </button>
      ) : (
        <form className="stack narrow" onSubmit={handleSubmit}>
          <label htmlFor="delete-password">Your password</label>
          <input
            id="delete-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <label htmlFor="delete-email">
            Type <strong>{user?.email ?? 'your email'}</strong> to confirm
          </label>
          <input
            id="delete-email"
            type="email"
            required
            value={confirmEmail}
            onChange={(e) => setConfirmEmail(e.target.value)}
          />

          {error && <p className="error" role="alert">{error}</p>}

          <div className="row gap">
            <button type="submit" className="danger-button" disabled={busy}>
              {busy ? 'Deleting…' : 'Permanently delete'}
            </button>
            <button type="button" className="secondary" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
