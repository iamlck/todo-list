import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const { acceptSession } = useAuth()
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (!token) {
    return (
      <main className="auth">
        <div className="card auth-card stack">
          <h1>Link incomplete</h1>
          <p className="muted">
            This reset link has no token. <Link to="/forgot-password">Request a new one</Link>.
          </p>
        </div>
      </main>
    )
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (password !== repeat) {
      setError('Those passwords do not match.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      // A successful reset signs you straight in, so you do not land on
      // another login form.
      acceptSession(await api.resetPassword(token, password))
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <h1>Choose a new password</h1>

        <label htmlFor="password">New password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="hint">At least 8 characters.</p>

        <label htmlFor="repeat">Repeat password</label>
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

        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Working…' : 'Set new password'}
        </button>

        <p className="muted">
          Your plan and progress are not affected. <Link to="/login">Back to sign in</Link>.
        </p>
      </form>
    </main>
  )
}
