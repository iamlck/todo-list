import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { usePlan } from '../context/PlanContext'
import UndoBar from './UndoBar'

export default function Layout() {
  const { signOut, user } = useAuth()
  const { loading, error, setError } = usePlan()

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to={user?.is_admin ? '/admin' : '/'} className="brand">
          Learning Tracker{user?.is_admin && <span className="brand-role"> admin</span>}
        </NavLink>
        <nav>
          {/* Administrators manage accounts; they do not follow a plan, so
              the tracker links are not theirs to see. */}
          {user?.is_admin ? (
            <NavLink to="/admin">Users</NavLink>
          ) : (
            <>
              <NavLink to="/" end>
                Dashboard
              </NavLink>
              <NavLink to="/time">Time</NavLink>
              <NavLink to="/editor">Edit plan</NavLink>
              <NavLink to="/history">History</NavLink>
            </>
          )}
          <NavLink to="/account">Account</NavLink>
        </nav>
        <div className="topbar-right">
          {user && <span className="muted email">{user.email}</span>}
          <button type="button" className="link" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      {error && (
        <div className="banner error" role="alert">
          <span>{error}</span>
          <button type="button" className="link" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <UndoBar />

      <main>
        {loading && !user?.is_admin ? (
          <p className="muted pad">Loading your plan…</p>
        ) : (
          <Outlet />
        )}
      </main>

      <footer className="footer muted">
        {user?.is_admin
          ? 'Administration. Account details only — never the contents of anyone\u2019s notes.'
          : 'A personal study tracker. It does not guarantee any exam result.'}
      </footer>
    </div>
  )
}
