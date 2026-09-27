import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Keeps the two roles apart.
 *
 * An administrator's job here is managing accounts, not following a study
 * plan, so they are sent to /admin rather than shown a tracker they do not
 * use. Ordinary users never see the admin area.
 */
export function UserOnly({ children }) {
  const { user } = useAuth()
  // `user` is null for a moment after a reload while /auth/me is in flight;
  // rendering nothing avoids a redirect based on a half-known session.
  if (!user) return null
  if (user.is_admin) return <Navigate to="/admin" replace />
  return children
}

export function AdminOnly({ children }) {
  const { user } = useAuth()
  if (!user) return null
  if (!user.is_admin) return <Navigate to="/" replace />
  return children
}
