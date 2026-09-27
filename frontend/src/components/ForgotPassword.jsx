import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (sent) {
    return (
      <main className="auth">
        <div className="card auth-card stack">
          <h1>Check the API log</h1>
          <p>
            If <strong>{email}</strong> has an account, a reset link has been created. It is
            valid for 30 minutes and can be used once.
          </p>
          <p className="muted">
            This app has no mail server, so the link is printed in the backend log rather than
            emailed. Find it with:
          </p>
          <code className="code-block">docker-compose logs --tail=20 api</code>
          <p className="muted">
            <Link to="/login">Back to sign in</Link>
          </p>
        </div>
      </main>
    )
  }

  return (
    <main className="auth">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <h1>Forgot your password?</h1>
        <p className="muted">
          Enter your email and we will create a reset link valid for 30 minutes.
        </p>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        {error && <p className="error" role="alert">{error}</p>}

        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Working…' : 'Send reset link'}
        </button>

        <p className="muted">
          Remembered it? <Link to="/login">Sign in</Link>.
        </p>
      </form>
    </main>
  )
}
