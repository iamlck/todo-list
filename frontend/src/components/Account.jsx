import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import DeleteAccount from './DeleteAccount'

export default function Account() {
  const { user } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (next !== repeat) {
      setError('The new passwords do not match.')
      return
    }
    setBusy(true)
    setError(null)
    setDone(false)
    try {
      await api.changePassword(current, next)
      setCurrent('')
      setNext('')
      setRepeat('')
      setDone(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="pad stack">
      <section className="card stack">
        <h1>Account</h1>
        {user && <p className="muted">Signed in as {user.email}.</p>}
      </section>

      <section className="card">
        <form className="stack narrow" onSubmit={handleSubmit}>
          <h2>Change password</h2>

          <label htmlFor="current">Current password</label>
          <input
            id="current"
            type="password"
            autoComplete="current-password"
            required
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />

          <label htmlFor="next">New password</label>
          <input
            id="next"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
          <p className="hint">At least 8 characters.</p>

          <label htmlFor="repeat">Repeat new password</label>
          <input
            id="repeat"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
          />

          {error && <p className="error" role="alert">{error}</p>}
          {done && <p className="ok" role="status">Password changed.</p>}

          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Working…' : 'Change password'}
          </button>
        </form>
      </section>

      <DeleteAccount />
    </div>
  )
}
